import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AccommodationService } from '../../../accommodation/services/accommodation.service';
import { TransportService } from '../../../transport/services/transport.service';
import { TrfService } from '../../services/trf.service';
import type { DomesticTravelSpecificDetails } from '../domestic-travel-details/domestic-travel-details.component';
import type { ExternalPartiesDetails } from '../external-parties-details/external-parties-details.component';
import type { OverseasTravelDetails } from '../overseas-travel-details/overseas-travel-details.component';
import type { RequestorInformation } from '../requestor-information/requestor-information.component';
import { formatDateForAPI } from './trf-data-mapper';
import type { NestedItineraryRow, PreparedTrfData } from './trf-wizard.types';

/**
 * Submission orchestration for the TRF wizard. Phase 3 of the
 * trf-wizard.component.ts size refactor (see
 * docs/TRF_WIZARD_REFACTOR_ROADMAP.md) - talks to
 * TrfService/AccommodationService/TransportService directly, so unlike
 * Phase 2's pure trf-data-mapper.ts functions this is a real injectable
 * service, not a plain module. The component still owns submitTrf() itself
 * (the final create/update + workflow-submit calls, toasts, navigation,
 * isSubmitting) - that's UI orchestration, not data preparation.
 */
export interface PrepareTrfDataParams {
  selectedTravelType: 'Domestic' | 'Overseas' | 'External Parties' | null;
  requestorData: Partial<RequestorInformation>;
  domesticTravelData: Partial<DomesticTravelSpecificDetails>;
  overseasTravelData: Partial<OverseasTravelDetails>;
  externalPartiesData: Partial<ExternalPartiesDetails>;
  additionalComments: string;
}

@Injectable({ providedIn: 'root' })
export class TrfSubmissionService {
  private trfService = inject(TrfService);
  private accommodationService = inject(AccommodationService);
  private transportService = inject(TransportService);

  /**
   * Prepare TRF data for submission
   */
  prepareTrfData(params: PrepareTrfDataParams): PreparedTrfData {
    // Main TRF data
    const mainTrf: Record<string, unknown> = {
      requestor_name: params.requestorData.fullName,
      staff_id: params.requestorData.staffId,
      department: params.requestorData.department,
      position: params.requestorData.position || '',
      cost_center: params.requestorData.costCenter,
      tel_email: params.requestorData.contactNo,
      email: params.requestorData.email,
      travel_type: params.selectedTravelType,
      // Always create as Draft, then call submit endpoint to generate request number
      status: 'Draft',
      estimated_cost: 0,
    };

    // Prepare data based on travel type
    switch (params.selectedTravelType) {
      case 'Domestic':
        return this.prepareDomesticData(mainTrf, params);
      case 'Overseas':
        return this.prepareOverseasData(mainTrf, params);
      case 'External Parties':
        return this.prepareExternalPartiesData(mainTrf, params);
      default:
        return {
          mainTrf,
          itinerarySegments: [],
          mealSelections: [],
          bankDetails: null,
          advanceAmounts: [],
        };
    }
  }

  /**
   * Prepare Domestic travel data
   */
  private prepareDomesticData(
    mainTrf: Record<string, unknown>,
    params: PrepareTrfDataParams
  ): PreparedTrfData {
    const { domesticTravelData } = params;
    mainTrf['purpose'] = domesticTravelData?.purposeOfTravel || '';
    mainTrf['additional_comments'] = params.additionalComments || '';

    return {
      mainTrf,
      itinerarySegments: (domesticTravelData?.itinerary || []) as unknown as NestedItineraryRow[],
      mealSelections: domesticTravelData?.mealProvisions?.dailySelections || [],
      bankDetails: null,
      advanceAmounts: [],
      accommodation: domesticTravelData?.accommodation || null,
      transport: domesticTravelData?.transport || null,
    };
  }

  /**
   * Prepare Overseas travel data
   */
  private prepareOverseasData(
    mainTrf: Record<string, unknown>,
    params: PrepareTrfDataParams
  ): PreparedTrfData {
    const { overseasTravelData } = params;
    mainTrf['purpose'] = overseasTravelData?.purpose || '';
    mainTrf['additional_comments'] = params.additionalComments || '';
    mainTrf['advance_consent_accepted'] = overseasTravelData?.advanceConsentAccepted || false;

    return {
      mainTrf,
      itinerarySegments: (overseasTravelData?.itinerary || []) as unknown as NestedItineraryRow[],
      mealSelections: [],
      bankDetails: overseasTravelData?.advanceBankDetails || null,
      advanceAmounts: overseasTravelData?.advanceAmountRequested || [],
    };
  }

  /**
   * Prepare External Parties data
   */
  private prepareExternalPartiesData(
    mainTrf: Record<string, unknown>,
    params: PrepareTrfDataParams
  ): PreparedTrfData {
    const { externalPartiesData } = params;
    mainTrf['purpose'] = externalPartiesData?.purpose || '';
    mainTrf['additional_comments'] = params.additionalComments || '';

    // Add external party specific fields - CORRECTED FIELD NAMES
    mainTrf['external_full_name'] = externalPartiesData?.externalFullName || '';
    mainTrf['external_organization'] = externalPartiesData?.externalOrganization || '';
    mainTrf['external_ref_to_authority_letter'] =
      externalPartiesData?.externalRefToAuthorityLetter || '';
    mainTrf['external_cost_center'] = externalPartiesData?.externalCostCenter || '';

    return {
      mainTrf,
      itinerarySegments: (externalPartiesData?.itinerary || []) as unknown as NestedItineraryRow[],
      mealSelections: [],
      bankDetails: null,
      advanceAmounts: [],
      accommodation: externalPartiesData?.accommodation || null,
      transport: externalPartiesData?.transport || null,
    };
  }

  /**
   * Delete existing nested resources for a TRF (used during update to prevent duplicates)
   */
  deleteExistingNestedResources(trfId: number): Promise<void> {
    const promises: Promise<unknown>[] = [];

    // Delete all existing nested resources - errors intentionally swallowed
    // (matching the caller's own comment: "some resources might not exist")
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'itinerary')).catch(() => {
        // Intentionally ignored - resource may not exist
      })
    );
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'meals')).catch(() => {
        // Intentionally ignored - resource may not exist
      })
    );
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'passport')).catch(() => {
        // Intentionally ignored - resource may not exist
      })
    );
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'bank')).catch(() => {
        // Intentionally ignored - resource may not exist
      })
    );
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'advance-amounts')).catch(() => {
        // Intentionally ignored - resource may not exist
      })
    );

    return Promise.all(promises).then(() => undefined);
  }

  /**
   * Create nested resources (itinerary, meals, passport, bank details, etc.)
   *
   * High cyclomatic complexity is 5 independent "if this section is present,
   * build its payload" blocks, not branchy control flow - splitting it up is
   * a real refactor better done on its own rather than folded into an
   * unrelated form-field removal.
   */
  // eslint-disable-next-line complexity
  async createNestedResources(
    trfId: number,
    data: PreparedTrfData,
    isDraft: boolean,
    isEditMode: boolean,
    requestorData: Partial<RequestorInformation>,
    passportFile: File | null,
    hasLinkedAccommodation: boolean = false,
    hasLinkedTransport: boolean = false
  ): Promise<boolean> {
    // Guard: Ensure trfId is valid
    if (!trfId || typeof trfId !== 'number' || trfId <= 0) {
      throw new Error(`Invalid TRF ID: ${trfId}`);
    }

    // If in edit mode, delete existing nested resources first to prevent duplicates
    if (isEditMode) {
      try {
        await this.deleteExistingNestedResources(trfId);
      } catch {
        // Continue anyway - some resources might not exist
      }
    }

    const promises: Promise<unknown>[] = [];

    // Create itinerary segments SEQUENTIALLY, not in parallel. The
    // backend has no explicit ordering field for segments - it infers
    // itinerary order from creation order (row id), matching how the
    // frontend appends them (see TrfItinerarySegmentSerializer.validate).
    // Firing these as concurrent, unawaited requests (as a .forEach
    // pushing into the shared `promises` array used to) races the
    // inserts: whichever request's transaction commits first gets the
    // lowest id, regardless of the segments' actual array/date order.
    // That scrambles the id order the backend relies on and causes it
    // to reject perfectly valid, correctly-ordered itineraries with a
    // false "date cannot be earlier than previous segment" error.
    if (data.itinerarySegments && data.itinerarySegments.length > 0) {
      for (const segment of data.itinerarySegments) {
        // Handle both standard fields (date, from, to) and External Parties fields (departureDate, departureLocation, arrivalLocation)
        const date = segment.date || segment.departureDate;
        const from = segment.from || segment.departureLocation;
        const to = segment.to || segment.arrivalLocation;

        // Skip segments with missing required fields
        if (!date || !from || !to) {
          continue;
        }

        const itineraryData = {
          trf: trfId,
          segment_date: formatDateForAPI(date),
          day_of_week: segment.day || '',
          from_location: from,
          to_location: to,
          departure_time: segment.departureTime || segment.etd || '',
          arrival_time: segment.arrivalTime || segment.eta || '',
          flight_number: segment.modeOfTransport || segment.flightNumber || '',
          remarks: segment.remarks || '',
        };

        await firstValueFrom(this.trfService.createItinerarySegment(itineraryData));
      }
    }

    // Create meal selections (Domestic only)
    if (data.mealSelections && data.mealSelections.length > 0) {
      data.mealSelections.forEach(meal => {
        // Skip meals with missing required meal_date
        if (!meal.date) {
          return;
        }

        const mealData = {
          trf: trfId,
          meal_date: formatDateForAPI(meal.date),
          breakfast: meal.breakfast || false,
          lunch: meal.lunch || false,
          dinner: meal.dinner || false,
          supper: meal.supper || false,
          refreshment: meal.refreshment || false,
        };

        promises.push(firstValueFrom(this.trfService.createDailyMeal(mealData)));
      });
    }

    // Create bank details (Overseas)
    if (data.bankDetails) {
      const bankData = {
        trf: trfId,
        bank_name: data.bankDetails.bankName || '',
        account_number: data.bankDetails.accountNumber || '',
        account_name: data.bankDetails.accountName || '',
        branch_address: data.bankDetails.branchAddress || '',
        currency: data.bankDetails.currency || 'USD',
      };

      promises.push(firstValueFrom(this.trfService.createBankDetail(bankData)));
    }

    // Create advance amount items (Overseas)
    if (data.advanceAmounts && data.advanceAmounts.length > 0) {
      data.advanceAmounts.forEach(amount => {
        const advanceData = {
          trf: trfId,
          date_from: amount.dateFrom || '',
          date_to: amount.dateTo || '',
          lh: amount.lh || 0,
          ma: amount.ma || 0,
          oa: amount.oa || 0,
          tr: amount.tr || 0,
          oe: amount.oe || 0,
          usd: amount.usd || 0,
          remarks: amount.remarks || '',
        };

        promises.push(firstValueFrom(this.trfService.createAdvanceAmountItem(advanceData)));
      });
    }

    // Create linked accommodation request (Domestic only, opt-in) - only on the
    // first real submission that produces one, i.e. only when this TRF doesn't
    // already have a linked accommodation request. Not gated on isEditMode:
    // editing a Draft to add "Requires Accommodation" and then submitting for
    // the first time is isEditMode=true but hasLinkedAccommodation=false, and
    // must still create it. What this guard protects against is re-creating an
    // already-submitted accommodation request on a later edit - it may already
    // be Assigned/processed by Accommodation Admin, so blindly delete-and-recreate
    // on every edit, like itinerary/meals do, would risk destroying that.
    // Editing accommodation details after first submission doesn't propagate to
    // the linked request yet - a known limitation, not a duplicate/data loss
    // risk. Reuses the existing AccommodationRequestViewSet create+submit actions
    // exactly as the standalone accommodation-create form does - no new backend
    // endpoints.
    if (!isDraft && !hasLinkedAccommodation && data.accommodation?.required) {
      const acc = data.accommodation;
      const accommodationData = {
        requestor_name: requestorData.fullName,
        staff_id: requestorData.staffId,
        department: requestorData.department,
        trf: trfId,
        additional_data: {
          requestor_gender: acc.gender,
          location: acc.location,
          requested_check_in_date: formatDateForAPI(acc.checkInDate) || acc.checkInDate,
          requested_check_out_date: formatDateForAPI(acc.checkOutDate) || acc.checkOutDate,
          requested_room_type: acc.roomType,
          flight_arrival_time: acc.checkInTime,
          flight_departure_time: acc.checkOutTime,
          special_requests: acc.specialRequests,
        },
      };

      promises.push(
        firstValueFrom(this.accommodationService.createRequest(accommodationData)).then(created =>
          firstValueFrom(this.accommodationService.submitRequest(created.id))
        )
      );
    }

    // Create linked transport request (Domestic only, opt-in) - only when this TRF
    // doesn't already have a linked transport request, same guarding as accommodation
    // above and for the same reason (an already-submitted transport request may
    // already be Assigned/processed by Transport Admin). Not gated on isEditMode -
    // see the accommodation block's comment above for why: a Draft being completed
    // and submitted for the first time is isEditMode=true but hasLinkedTransport=
    // false, and must still create the transport request (previously it silently
    // never did, so a TSR saved as a Draft with "Requires Transport" checked, then
    // reopened later to finish and submit, would submit successfully with zero
    // linked transport and no error shown anywhere). Unlike accommodation,
    // Transport's own WorkflowTemplate stays active for ad-hoc requests - setting
    // `trf` here is what makes TransportRequestViewSet skip starting a separate
    // workflow for this one, so it rides the TSR's approval instead (see
    // WorkflowEngine._cascade_status_to_linked_transport). Matches the standalone
    // transport-create form's own single-call pattern exactly (status: 'Pending' sent
    // directly in the create payload - transport-create.component.ts does the same,
    // unlike accommodation-create's create-then-submit two-call pattern) - no new
    // backend endpoints.
    if (!isDraft && !hasLinkedTransport && data.transport?.required) {
      const transport = data.transport;
      const transportData = {
        requestor_name: requestorData.fullName,
        staff_id: requestorData.staffId,
        department: requestorData.department,
        position: requestorData.position,
        // No separate purpose field on this embedded section (see
        // TransportDetails) - reuse the TSR's own purpose so the linked
        // transport request's required `purpose` field is still satisfied.
        purpose: data.mainTrf?.['purpose'] || '',
        status: 'Pending',
        trf: trfId,
        transport_details: (transport.journeys || []).map(j => ({
          date: formatDateForAPI(j.date) || j.date,
          day: j.day,
          from: j.from,
          to: j.to,
          departure_time: j.departureTime,
          number_of_passengers: j.numberOfPassengers,
        })),
      };

      promises.push(firstValueFrom(this.transportService.createRequest(transportData)));
    }

    // Upload passport file if provided
    if (passportFile) {
      promises.push(firstValueFrom(this.trfService.uploadPassportDocument(trfId, passportFile)));
    }

    // Wait for all nested resources to be created
    await Promise.all(promises);
    return true;
  }
}
