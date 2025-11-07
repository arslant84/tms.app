// Expense Claim Models matching React source types exactly

export type DocumentType = "TR01" | "TB35" | "TB05" | "";
export type StaffType = "PERMANENT STAFF" | "CONTRACT STAFF" | "";
export type ExecutiveStatus = "EXECUTIVE" | "NON-EXECUTIVE" | "";
export type MedicalClaimApplicable = "Inpatient" | "Outpatient" | "" | undefined;

export type ClaimStatus =
  | 'Pending Verification'
  | 'Pending Department Focal'
  | 'Pending Line Manager'
  | 'Pending HOD'
  | 'Approved'
  | 'Processing with Claims Admin'
  | 'Processed'
  | 'Rejected'
  | 'Cancelled'
  | 'Draft';

export interface ClaimHeaderDetails {
  documentType: DocumentType;
  documentNumber: string;
  claimForMonthOf: Date | string | null;
  staffName: string;
  staffNo: string;
  gred: string; // Grade
  staffType: StaffType;
  executiveStatus: ExecutiveStatus;
  departmentCode: string;
  deptCostCenterCode: string;
  location: string;
  telExt: string;
  startTimeFromHome: string; // HH:MM
  timeOfArrivalAtHome: string; // HH:MM
}

export interface ClaimantBankDetails {
  bankName: string;
  accountNumber: string;
  purposeOfClaim: string;
}

export interface MedicalClaimDetails {
  isMedicalClaim: boolean;
  applicableMedicalType?: MedicalClaimApplicable;
  isForFamily: boolean;
  familyMemberSpouse: boolean;
  familyMemberChildren: boolean;
  familyMemberOther?: string; // Description for other
}

export interface ClaimOrTravelDetails {
  from?: string;
  to?: string;
  placeOfStay?: string;
}

export interface ExpenseItem {
  id?: string | number;
  date: Date | string | null;
  claimOrTravelDetails: string | ClaimOrTravelDetails; // Can be string or object
  officialMileageKM: string | number | null; // B
  transport: string | number | null; // C
  hotelAccommodationAllowance: string | number | null; // D
  outStationAllowanceMeal: string | number | null; // E
  miscellaneousAllowance10Percent: string | number | null; // F
  otherExpenses: string | number | null; // G
}

export interface ForeignExchangeRate {
  id?: string | number;
  date: Date | string | null;
  typeOfCurrency: string;
  sellingRateTTOD: string | number | null;
}

export interface ClaimFinancialSummary {
  totalAdvanceClaimAmount: string | number | null;
  lessAdvanceTaken: string | number | null;
  lessCorporateCreditCardPayment: string | number | null;
  balanceClaimRepayment: string | number | null; // Calculated
  chequeReceiptNo?: string;
}

export interface ClaimDeclaration {
  iDeclare: boolean;
  date: Date | string | null;
}

export interface ReimbursementDetails {
  paymentMethod?: string; // Bank Transfer, Cheque, etc.
  bankTransferReference?: string;
  chequeNumber?: string;
  paymentDate?: string;
  amountPaid?: number;
  taxDeducted?: number;
  netAmount?: number;
  processingNotes?: string;
  verifiedBy?: string;
  authorizedBy?: string;
}

export interface ExpenseClaim {
  id?: string | number;
  headerDetails: ClaimHeaderDetails;
  bankDetails: ClaimantBankDetails;
  medicalClaimDetails: MedicalClaimDetails;
  expenseItems: ExpenseItem[];
  informationOnForeignExchangeRate: ForeignExchangeRate[];
  financialSummary: ClaimFinancialSummary;
  declaration: ClaimDeclaration;

  // Status information
  status?: ClaimStatus;
  submittedAt?: string;

  // Claims Admin processing fields
  reimbursementDetails?: ReimbursementDetails;
  processingStartedAt?: string;
  reimbursementCompletedAt?: string;
  createdBy?: string;
  updatedBy?: string;
  created_at?: string;
  updated_at?: string;
}

// Approval Step interface
export interface ClaimsApprovalStep {
  id?: number;
  claim_id?: number;
  step_role: string;
  step_name: string;
  status: string;
  step_date?: string;
  comments?: string;
  approved_by?: string;
}

// Extended interface for detail view with approval steps
export interface ExpenseClaimDetail extends ExpenseClaim {
  approval_steps?: ClaimsApprovalStep[];
}

// Backend compatibility interfaces (for API communication)
export interface ExpenseClaimBackend {
  id: number;
  request_number?: string;
  title: string;
  description: string;
  total_amount: number;
  currency: string;
  expense_date: string;
  category: string;
  status: string;
  receipt_urls?: string[];
  additional_data?: any;
  created_at: string;
  updated_at?: string;
  submitted_at?: string;
  user_id?: number;
  user_name?: string;
  user_email?: string;
  trf_id?: number;
  trf_reference?: string;
  items?: any[];
  approval_steps?: ClaimsApprovalStep[];
}

export interface ExpenseClaimItemBackend {
  id?: number;
  claim_id?: number;
  item_date: string;
  claim_or_travel_details: string;
  official_mileage_km?: number;
  transport?: number;
  hotel_accommodation_allowance?: number;
  out_station_allowance_meal?: number;
  miscellaneous_allowance_10_percent?: number;
  other_expenses?: number;
}

export interface ExpenseClaimFXRateBackend {
  id?: number;
  claim_id?: number;
  fx_date: string;
  type_of_currency: string;
  selling_rate_tt_od: number;
}

// Helper function to convert frontend model to backend format
export function toBackendFormat(claim: ExpenseClaim, defaultCurrency: string = 'USD'): any {
  // Convert travel details object to string if needed
  const convertTravelDetails = (details: string | ClaimOrTravelDetails): string => {
    if (typeof details === 'string') return details;
    const parts = [];
    if (details.from) parts.push(`From: ${details.from}`);
    if (details.to) parts.push(`To: ${details.to}`);
    if (details.placeOfStay) parts.push(`Place: ${details.placeOfStay}`);
    return parts.join(', ');
  };

  // Calculate total amount from all expense items
  const calculateTotalAmount = (): number => {
    return claim.expenseItems.reduce((total, item) => {
      const itemTotal = (
        (Number(item.transport) || 0) +
        (Number(item.hotelAccommodationAllowance) || 0) +
        (Number(item.outStationAllowanceMeal) || 0) +
        (Number(item.miscellaneousAllowance10Percent) || 0) +
        (Number(item.otherExpenses) || 0)
      );
      return total + itemTotal;
    }, 0);
  };

  // Format date to YYYY-MM-DD
  const formatDate = (date: Date | string | null): string => {
    if (!date) return new Date().toISOString().split('T')[0];

    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return new Date().toISOString().split('T')[0];

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // Get first expense date or use claim date
  const getExpenseDate = (): string => {
    if (claim.expenseItems && claim.expenseItems.length > 0 && claim.expenseItems[0].date) {
      return formatDate(claim.expenseItems[0].date);
    }
    if (claim.headerDetails?.claimForMonthOf) {
      return formatDate(claim.headerDetails.claimForMonthOf);
    }
    return formatDate(new Date());
  };

  // Determine category based on item amounts
  const determineCategory = (item: any): string => {
    // Valid backend categories: ACCOMMODATION, MEALS, TRANSPORTATION, ENTERTAINMENT, MISCELLANEOUS
    if (Number(item.hotelAccommodationAllowance) > 0) return 'ACCOMMODATION';
    if (Number(item.transport) > 0) return 'TRANSPORTATION';
    if (Number(item.outStationAllowanceMeal) > 0) return 'MEALS';
    return 'MISCELLANEOUS';
  };

  // Map expense items to backend format
  const mapExpenseItems = () => {
    return claim.expenseItems.map(item => {
      const travelDetails = convertTravelDetails(item.claimOrTravelDetails);
      const itemAmount = (
        (Number(item.transport) || 0) +
        (Number(item.hotelAccommodationAllowance) || 0) +
        (Number(item.outStationAllowanceMeal) || 0) +
        (Number(item.miscellaneousAllowance10Percent) || 0) +
        (Number(item.otherExpenses) || 0)
      );

      return {
        description: travelDetails || 'Expense item',
        amount: itemAmount,
        category: determineCategory(item),
        date: formatDate(item.date),
        receipt_url: ''
      };
    });
  };

  // Build the title from document type and number
  const buildTitle = (): string => {
    const docType = claim.headerDetails?.documentType || 'Expense Claim';
    const docNumber = claim.headerDetails?.documentNumber || '';
    return docNumber ? `${docType} - ${docNumber}` : docType;
  };

  // Build description from purpose and staff info
  const buildDescription = (): string => {
    const parts = [];
    if (claim.bankDetails?.purposeOfClaim) {
      parts.push(claim.bankDetails.purposeOfClaim);
    }
    if (claim.headerDetails?.staffName) {
      parts.push(`Staff: ${claim.headerDetails.staffName} (${claim.headerDetails.staffNo || 'N/A'})`);
    }
    if (claim.headerDetails?.departmentCode) {
      parts.push(`Department: ${claim.headerDetails.departmentCode}`);
    }
    return parts.join(' | ') || 'Expense Claim';
  };

  // Determine overall category for the claim
  const getClaimCategory = (): string => {
    // Check if most items are of a specific type
    const items = claim.expenseItems || [];
    if (items.length === 0) return 'MISCELLANEOUS';

    let hasAccommodation = false;
    let hasTransportation = false;
    let hasMeals = false;

    items.forEach(item => {
      if (Number(item.hotelAccommodationAllowance) > 0) hasAccommodation = true;
      if (Number(item.transport) > 0) hasTransportation = true;
      if (Number(item.outStationAllowanceMeal) > 0) hasMeals = true;
    });

    // Return most relevant category
    if (hasAccommodation) return 'ACCOMMODATION';
    if (hasTransportation) return 'TRANSPORTATION';
    if (hasMeals) return 'MEALS';
    return 'MISCELLANEOUS';
  };

  // Return the simple backend format that matches ExpenseClaimCreateSerializer
  return {
    trf: null, // No TRF linkage for now
    title: buildTitle(),
    description: buildDescription(),
    total_amount: calculateTotalAmount(),
    currency: defaultCurrency, // Use currency from settings
    expense_date: getExpenseDate(),
    category: getClaimCategory(),
    receipt_urls: [],
    items: mapExpenseItems(),
    // Store full complex data in additional_data for retrieval
    additional_data: {
      headerDetails: claim.headerDetails,
      bankDetails: claim.bankDetails,
      medicalClaimDetails: claim.medicalClaimDetails,
      financialSummary: claim.financialSummary,
      declaration: claim.declaration,
      informationOnForeignExchangeRate: claim.informationOnForeignExchangeRate,
      expenseItems: claim.expenseItems
    }
  };
}

// Helper function to convert backend model to frontend format
export function toFrontendFormat(backendClaim: ExpenseClaimBackend): ExpenseClaim {
  // Convert backend status (UPPERCASE) to match backend format for consistency
  // Backend uses: DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, PAID
  // We'll keep the backend format as-is since the component already handles both
  const normalizedStatus = backendClaim.status;

  // If additional_data exists, use it (new format)
  if (backendClaim.additional_data) {
    const ad = backendClaim.additional_data;
    return {
      id: backendClaim.id,
      headerDetails: ad.headerDetails || {
        documentType: "" as DocumentType,
        documentNumber: "",
        claimForMonthOf: null,
        staffName: "",
        staffNo: "",
        gred: "",
        staffType: "" as StaffType,
        executiveStatus: "" as ExecutiveStatus,
        departmentCode: "",
        deptCostCenterCode: "",
        location: "",
        telExt: "",
        startTimeFromHome: "",
        timeOfArrivalAtHome: ""
      },
      bankDetails: ad.bankDetails || {
        bankName: "",
        accountNumber: "",
        purposeOfClaim: ""
      },
      medicalClaimDetails: ad.medicalClaimDetails || {
        isMedicalClaim: false,
        isForFamily: false,
        familyMemberSpouse: false,
        familyMemberChildren: false
      },
      expenseItems: ad.expenseItems || [],
      informationOnForeignExchangeRate: ad.informationOnForeignExchangeRate || [],
      financialSummary: ad.financialSummary || {
        totalAdvanceClaimAmount: null,
        lessAdvanceTaken: null,
        lessCorporateCreditCardPayment: null,
        balanceClaimRepayment: null
      },
      declaration: ad.declaration || {
        iDeclare: false,
        date: null
      },
      status: normalizedStatus as ClaimStatus,
      submittedAt: backendClaim.submitted_at,
      created_at: backendClaim.created_at,
      updated_at: backendClaim.updated_at
    };
  }

  // Fallback for old format or missing additional_data
  return {
    id: backendClaim.id,
    headerDetails: {
      documentType: "" as DocumentType,
      documentNumber: "",
      claimForMonthOf: null,
      staffName: "",
      staffNo: "",
      gred: "",
      staffType: "" as StaffType,
      executiveStatus: "" as ExecutiveStatus,
      departmentCode: "",
      deptCostCenterCode: "",
      location: "",
      telExt: "",
      startTimeFromHome: "",
      timeOfArrivalAtHome: ""
    },
    bankDetails: {
      bankName: "",
      accountNumber: "",
      purposeOfClaim: backendClaim.description || ""
    },
    medicalClaimDetails: {
      isMedicalClaim: false,
      isForFamily: false,
      familyMemberSpouse: false,
      familyMemberChildren: false
    },
    expenseItems: [],
    informationOnForeignExchangeRate: [],
    financialSummary: {
      totalAdvanceClaimAmount: backendClaim.total_amount,
      lessAdvanceTaken: null,
      lessCorporateCreditCardPayment: null,
      balanceClaimRepayment: null
    },
    declaration: {
      iDeclare: false,
      date: null
    },
    status: normalizedStatus as ClaimStatus,
    submittedAt: backendClaim.submitted_at,
    created_at: backendClaim.created_at,
    updated_at: backendClaim.updated_at
  };
}
