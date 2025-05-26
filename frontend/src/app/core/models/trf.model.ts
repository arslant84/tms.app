export interface TravelRequestForm {
  id: string;
  requesterId: string;
  requesterName: string;
  purpose: string;
  destination: string;
  departureDate: Date;
  returnDate: Date;
  travelType: TravelType;
  accommodationRequired: boolean;
  estimatedCost: number;
  status: TRFStatus;
  approvalChain: ApprovalStep[];
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

export enum TravelType {
  DOMESTIC = 'DOMESTIC',
  INTERNATIONAL = 'INTERNATIONAL'
}

export enum TRFStatus {
  DRAFT = 'DRAFT',
  SUBMITTED = 'SUBMITTED',
  PENDING_APPROVAL = 'PENDING_APPROVAL',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  CANCELLED = 'CANCELLED'
}

export interface ApprovalStep {
  approverId: string;
  approverName: string;
  status: ApprovalStatus;
  comments?: string;
  timestamp?: Date;
}

export enum ApprovalStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED'
}
