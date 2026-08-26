import { Injectable, inject } from '@angular/core';
import { map, catchError } from 'rxjs/operators';
import { Observable, of } from 'rxjs';
import { AccommodationService } from '../../../accommodation/services/accommodation.service';
import { TransportService } from '../../../transport/services/transport.service';
import { TrfService } from '../../services/trf.service';
import type { RequestorInformation } from '../requestor-information/requestor-information.component';
import type { ApprovalSubmissionData } from '../approval-submission/approval-submission.component';
import type {
  AccommodationDetails,
  DomesticTravelSpecificDetails,
  ItinerarySegment as DomesticItinerarySegment,
  TransportDetails,
  TransportJourney,
} from '../domestic-travel-details/domestic-travel-details.component';
import type {
  ItinerarySegment as OverseasItinerarySegment,
  OverseasTravelDetails,
} from '../overseas-travel-details/overseas-travel-details.component';
import type { HomeLeaveDetails } from '../home-leave-details/home-leave-details.component';
import type { ExternalPartiesDetails } from '../external-parties-details/external-parties-details.component';
import {
  deriveTripTypeFromItinerary,
  extractPassportFileInfo,
  transformAdvanceAmounts,
  transformBankDetails,
  transformExternalPartiesItineraryData,
  transformItineraryData,
  transformMealSelectionsData,
  transformPassportDetails,
} from './trf-data-mapper';
import type {
  NestedItineraryRow,
  RawAdvanceAmountRow,
  RawBankDetailRow,
  RawMealRow,
  RawPassportRow,
  TransformedPassportDetails,
  TrfBackendResponse,
} from './trf-wizard.types';

type SelectedTravelType = 'Domestic' | 'Overseas' | 'Home Leave' | 'External Parties' | null;

export interface TravelTypeEditResult {
  domesticTravelData?: Partial<DomesticTravelSpecificDetails>;
  overseasTravelData?: Partial<OverseasTravelDetails>;
  homeLeaveData?: Partial<HomeLeaveDetails> & {
    passportDetails?: TransformedPassportDetails | null;
  };
  externalPartiesData?: Partial<ExternalPartiesDetails>;
}

/**
 * Edit-mode data loading for the TRF wizard. Phase 4 of the
 * trf-wizard.component.ts size refactor (see
 * docs/TRF_WIZARD_REFACTOR_ROADMAP.md) - the reverse direction of Phase 3:
 * fetches and transforms an existing TRF's backend data into the shape each
 * step's form expects. Not pure (talks to
 * TrfService/AccommodationService/TransportService), and unlike Phase 3,
 * returns plain result objects rather than mutating component state - the
 * component assigns them into its own `this.*TravelData` fields.
 */
@Injectable({ providedIn: 'root' })
export class TrfEditLoaderService {
  private trfService = inject(TrfService);
  private accommodationService = inject(AccommodationService);
  private transportService = inject(TransportService);

  /**
   * Fetch a TRF for editing and unwrap the backend's { trf: {...} }
   * wrapper shape, if present.
   *
   * TrfService.getTrfById() is typed Observable<TravelRequestForm>, but
   * that model (core/models/trf.model.ts) is a stale/mock shape that
   * doesn't match what the endpoint actually returns (this file has always
   * read requestor_name/staff_id/etc., none of which exist on
   * TravelRequestForm) - out of scope to fix trf.service.ts's typing here,
   * so cast at this boundary to the shape this file actually consumes
   * instead of trusting the declared (wrong) type.
   */
  loadForEdit(id: number, hasAdminView: boolean): Observable<TrfBackendResponse> {
    return this.trfService.getTrfById(id, false, hasAdminView).pipe(
      map(response => {
        const raw = response as unknown as TrfBackendResponse;
        return raw.trf || raw;
      })
    );
  }

  /** Allow editing for Draft, Rejected, or any Pending status. */
  canEditStatus(status: string | undefined): boolean {
    return status === 'Draft' || status === 'Rejected' || !!status?.startsWith('Pending');
  }

  buildRequestorData(data: TrfBackendResponse): Partial<RequestorInformation> {
    return {
      fullName: data.requestor_name || data.requestorName,
      staffId: data.staff_id || data.staffId,
      department: data.department,
      position: data.position,
      costCenter: data.cost_center || data.costCenter,
      contactNo: data.tel_email || data.telEmail,
      email: data.email,
    };
  }

  buildApprovalData(data: TrfBackendResponse): Partial<ApprovalSubmissionData> {
    return {
      additionalComments: data.additional_comments || data.additionalComments || '',
      selected_approvers: data.selected_approvers || {},
      skipped_steps: data.skipped_steps || {},
      approved_step_orders: data.approved_step_orders || [],
    };
  }

  /**
   * Pre-populate travel-specific data
   *
   * High cyclomatic complexity is a 4-branch switch over travel type, each
   * branch a straight-line field mapping from the backend's nested response
   * shape - not genuinely branchy logic. A real refactor (e.g. one mapper
   * method per travel type) is better done on its own rather than folded
   * into an unrelated form-field removal.
   */
  // eslint-disable-next-line complexity
  buildTravelTypeData(
    selectedTravelType: SelectedTravelType,
    data: TrfBackendResponse
  ): TravelTypeEditResult {
    switch (selectedTravelType) {
      case 'Domestic': {
        // Backend returns nested structure: data.domesticTravelDetails.itinerary
        const domesticDetails = data.domesticTravelDetails || {};
        const itineraryData =
          domesticDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const mealData =
          domesticDetails.mealProvision?.dailyMealSelections ||
          data.daily_meals ||
          data.daily_meal_selections ||
          data.mealSelections ||
          [];
        const domesticPassport = extractPassportFileInfo(
          (data.passport_details || data.passportDetails) as RawPassportRow | RawPassportRow[]
        );

        const domesticItinerary = transformItineraryData(itineraryData as NestedItineraryRow[]);
        return {
          domesticTravelData: {
            purposeOfTravel: domesticDetails.purpose || data.purpose || '',
            tripType: deriveTripTypeFromItinerary(
              domesticItinerary as unknown as Record<string, unknown>[],
              'from',
              'to',
              'date'
            ),
            itinerary: domesticItinerary as unknown as DomesticItinerarySegment[],
            mealProvisions: {
              dailySelections: transformMealSelectionsData(mealData as RawMealRow[]),
            },
            passportUpload: domesticPassport,
          },
        };
      }

      case 'Overseas': {
        // Backend returns nested structure: data.overseasTravelDetails
        const overseasDetails = data.overseasTravelDetails || {};
        const overseasItinerary =
          overseasDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const bankDetails =
          overseasDetails.advanceBankDetails ||
          data.bank_detail ||
          data.advance_bank_details ||
          data.bankDetails;
        const advanceAmounts =
          overseasDetails.advanceAmountRequested ||
          data.advance_amounts ||
          data.advance_amount_items ||
          data.advanceAmounts ||
          [];
        const overseasPassport = extractPassportFileInfo(
          (data.passport_details || data.passportDetails) as RawPassportRow | RawPassportRow[]
        );

        const overseasTransformedItinerary = transformItineraryData(
          overseasItinerary as NestedItineraryRow[]
        );
        return {
          overseasTravelData: {
            purpose: overseasDetails.purpose || data.purpose || '',
            tripType: deriveTripTypeFromItinerary(
              overseasTransformedItinerary as unknown as Record<string, unknown>[],
              'from',
              'to',
              'date'
            ),
            itinerary: overseasTransformedItinerary as unknown as OverseasItinerarySegment[],
            advanceBankDetails: transformBankDetails(bankDetails as RawBankDetailRow),
            advanceAmountRequested: transformAdvanceAmounts(
              advanceAmounts as RawAdvanceAmountRow[]
            ),
            advanceConsentAccepted: data.advance_consent_accepted || false,
            passportUpload: overseasPassport,
          },
        };
      }

      case 'Home Leave': {
        // Backend returns nested structure: data.overseasTravelDetails (Home Leave reuses overseas structure)
        const homeLeaveDetails = data.overseasTravelDetails || {};
        const homeLeaveItinerary =
          homeLeaveDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const passportDetails = (data.passport_details || data.passportDetails) as
          | RawPassportRow
          | RawPassportRow[];
        const homeLeaveBank =
          homeLeaveDetails.advanceBankDetails ||
          data.bank_detail ||
          data.advance_bank_details ||
          data.bankDetails;
        const homeLeaveAdvanceAmounts =
          homeLeaveDetails.advanceAmountRequested ||
          data.advance_amounts ||
          data.advance_amount_items ||
          data.advanceAmounts ||
          [];
        const homeLeavePassport = extractPassportFileInfo(passportDetails);

        const homeLeaveTransformedItinerary = transformItineraryData(
          homeLeaveItinerary as NestedItineraryRow[]
        );
        return {
          homeLeaveData: {
            purpose: homeLeaveDetails.purpose || data.purpose || '',
            tripType: deriveTripTypeFromItinerary(
              homeLeaveTransformedItinerary as unknown as Record<string, unknown>[],
              'from',
              'to',
              'date'
            ),
            itinerary: homeLeaveTransformedItinerary,
            passportDetails: transformPassportDetails(passportDetails),
            advanceBankDetails: transformBankDetails(homeLeaveBank as RawBankDetailRow),
            advanceAmountRequested: transformAdvanceAmounts(
              homeLeaveAdvanceAmounts as RawAdvanceAmountRow[]
            ),
            advanceConsentAccepted: data.advance_consent_accepted || false,
            passportUpload: homeLeavePassport,
          },
        };
      }

      case 'External Parties': {
        // Backend returns nested structure: data.externalPartiesTravelDetails
        const externalDetails = data.externalPartiesTravelDetails || {};
        const externalRequestorInfo = data.externalPartyRequestorInfo || {};
        const externalItinerary =
          externalDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const externalPassport = extractPassportFileInfo(
          (data.passport_details || data.passportDetails) as RawPassportRow | RawPassportRow[]
        );

        const externalTransformedItinerary = transformExternalPartiesItineraryData(
          externalItinerary as NestedItineraryRow[]
        );
        return {
          externalPartiesData: {
            purpose: externalDetails.purpose || data.purpose || '',
            tripType: deriveTripTypeFromItinerary(
              externalTransformedItinerary as unknown as Record<string, unknown>[],
              'departureLocation',
              'arrivalLocation',
              'departureDate',
              'departureTime'
            ),
            externalFullName:
              externalRequestorInfo.externalFullName ||
              data.external_full_name ||
              data.externalFullName ||
              '',
            externalOrganization:
              externalRequestorInfo.externalOrganization ||
              data.external_organization ||
              data.externalOrganization ||
              '',
            externalRefToAuthorityLetter:
              externalRequestorInfo.externalRefToAuthorityLetter ||
              data.external_ref_to_authority_letter ||
              data.externalRefToAuthorityLetter ||
              '',
            externalCostCenter:
              externalRequestorInfo.externalCostCenter ||
              data.external_cost_center ||
              data.externalCostCenter ||
              '',
            itinerary: externalTransformedItinerary,
            passportUpload: externalPassport,
          },
        };
      }

      default:
        return {};
    }
  }

  /**
   * Accommodation requests embedded in a TSR are linked via AccommodationRequest.trf,
   * not returned as part of the TRF payload itself (same reasoning as
   * trf-detail.component.ts's loadLinkedAccommodation). When editing an existing
   * Domestic TRF, fetch its linked accommodation request (if any) so the
   * "Requires Accommodation" section can pre-populate instead of always
   * starting blank. Returns null (rather than throwing) on error or when
   * no linked request exists - non-critical, the rest of the edit form
   * still works without it.
   */
  loadLinkedAccommodation(trfId: number): Observable<AccommodationDetails | null> {
    // AccommodationService.getAllRequests() is typed Observable<any> at its
    // own declaration (out of scope to fix here) - this interface describes
    // only the fields this call site actually reads off each row.
    interface LinkedAccommodationRow {
      trf?: number;
      additional_data?: {
        requestor_gender?: string;
        location?: string;
        requested_check_in_date?: string;
        flight_arrival_time?: string;
        requested_check_out_date?: string;
        flight_departure_time?: string;
        requested_room_type?: string;
        special_requests?: string;
      };
    }

    return this.accommodationService.getAllRequests({ page_size: 100 }).pipe(
      map((response: { results?: LinkedAccommodationRow[] } | LinkedAccommodationRow[]) => {
        const results = (Array.isArray(response) ? response : response?.results) || [];
        const linked = results.find(req => req.trf === trfId);
        if (!linked) {
          return null;
        }
        const additionalData = linked.additional_data || {};
        // gender/location/roomType are backend free-text that this form's
        // AccommodationDetails narrows to specific literal unions - trust
        // the backend value the same way the rest of this file already
        // trusts loosely-typed API responses rather than validating every
        // possible literal here.
        return {
          required: true,
          gender: (additionalData.requestor_gender || '') as AccommodationDetails['gender'],
          location: (additionalData.location || '') as AccommodationDetails['location'],
          checkInDate: additionalData.requested_check_in_date || '',
          checkInTime: additionalData.flight_arrival_time || '',
          checkOutDate: additionalData.requested_check_out_date || '',
          checkOutTime: additionalData.flight_departure_time || '',
          roomType: (additionalData.requested_room_type || '') as AccommodationDetails['roomType'],
          specialRequests: additionalData.special_requests || '',
        };
      }),
      catchError(() => of(null))
    );
  }

  /**
   * Transport requests embedded in a TSR are linked via TransportRequest.trf, not
   * returned as part of the TRF payload itself - same reasoning/pattern as
   * loadLinkedAccommodation above.
   */
  loadLinkedTransport(trfId: number): Observable<TransportDetails | null> {
    // TransportService.getAllRequests() is typed Observable<any> at its own
    // declaration (out of scope to fix here) - this interface describes
    // only the fields this call site actually reads off each row.
    interface LinkedTransportRow {
      trfId?: number | string;
      transportDetails?: TransportJourney[];
    }

    return this.transportService.getAllRequests({ page_size: 100 }).pipe(
      map((response: { results?: LinkedTransportRow[] } | LinkedTransportRow[]) => {
        const results = (Array.isArray(response) ? response : response?.results) || [];
        const linked = results.find(req => Number(req.trfId) === trfId);
        if (!linked) {
          return null;
        }
        return {
          required: true,
          journeys: linked.transportDetails || [],
        };
      }),
      catchError(() => of(null))
    );
  }
}
