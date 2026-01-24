export interface EmployeeDetails {
  fullName: string;
  staffId: string;
  department: string;
  position: string;
  deptCostCenter: string;
  telExt: string;
  email: string;
}

export interface TravelItineraryItem {
  date: string;
  day: string;
  from: string;
  to: string;
  etd: string; // Estimated Time of Departure
  eta: string; // Estimated Time of Arrival
  flight: string;
  remarks: string;
}

export interface MealProvision {
  date: string;
  breakfast: boolean;
  lunch: boolean;
  dinner: boolean;
  supper: boolean;
  refreshment: boolean;
}

export interface Approval {
  preparedBy: string;
  preparedByPosition: string;
  preparedByDate: string;
  reviewedBy: string;
  reviewedByPosition: string;
  reviewedByDate: string;
  approvedBy: string;
  approvedByPosition: string;
  approvedByDate: string;
}

// Currency types for overseas travel
export type CurrencyType = 'LM' | 'MA' | 'OA' | 'JK' | 'OE' | 'USD' | 'TBM';

// Amount requested item for overseas travel
export interface AmountRequestedItem {
  date: string;
  to: string;
  currencyType: CurrencyType;
  amount: number;
  remarks: string;
}

// Bank details for overseas travel
export interface BankDetails {
  bankName: string;
  accountNumber: string;
}

export interface DomesticTravelRequestForm {
  id?: number;
  employeeDetails: EmployeeDetails;
  purposeOfTravel: string;
  itinerary: TravelItineraryItem[];
  mealProvisions: MealProvision[];
  approval: Approval;
  status: 'Draft' | 'Submitted' | 'UnderReview' | 'Approved' | 'Rejected';
  createdAt: string;
  updatedAt: string;
}

export interface OverseasTravelRequestForm {
  id?: number;
  employeeDetails: EmployeeDetails;
  purposeOfTravel: string;
  itinerary: TravelItineraryItem[];
  bankDetails: BankDetails;
  amountRequested: AmountRequestedItem[];
  termsAccepted: boolean;
  signature: string;
  signatureDate: string;
  approval: Approval;
  status: 'Draft' | 'Submitted' | 'UnderReview' | 'Approved' | 'Rejected';
  createdAt: string;
  updatedAt: string;
}

// Passport upload interface for all travel types
export interface PassportUpload {
  file: File | null;
  fileName?: string;
  fileUrl?: string;
}

// Passport detail with file support
export interface PassportDetailWithFile {
  id?: number;
  fullName?: string;
  passportNumber?: string;
  nationality?: string;
  dateOfBirth?: string;
  placeOfBirth?: string;
  passportIssueDate?: string;
  passportExpiryDate?: string;
  passportFile?: File | null;
  passportFileUrl?: string;
}

// Union type for all travel request forms
export type TravelRequestForm = DomesticTravelRequestForm | OverseasTravelRequestForm;

// Type guard to check if a form is an overseas form
export function isOverseasTravelRequestForm(form: TravelRequestForm): form is OverseasTravelRequestForm {
  return 'bankDetails' in form;
}
