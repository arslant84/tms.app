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

export interface Accommodation {
  type: 'Hotel' | 'StaffHouse' | 'PKCKampung' | 'Other';
  otherDetails?: string;
  checkInDate: string;
  checkInTime: string;
  checkOutDate: string;
  checkOutTime: string;
  remarks: string;
}

export interface CompanyTransportation {
  date: string;
  day: string;
  from: string;
  to: string;
  etd: string;
  accommodationType: string;
  address: string;
  remarks: string;
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

export interface DomesticTravelRequestForm {
  id?: number;
  employeeDetails: EmployeeDetails;
  purposeOfTravel: string;
  itinerary: TravelItineraryItem[];
  mealProvisions: MealProvision[];
  accommodation: Accommodation;
  companyTransportation: CompanyTransportation[];
  approval: Approval;
  status: 'Draft' | 'Submitted' | 'UnderReview' | 'Approved' | 'Rejected';
  createdAt: string;
  updatedAt: string;
}
