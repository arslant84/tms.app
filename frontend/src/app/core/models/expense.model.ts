export interface ExpenseClaim {
  id: string;
  trfId?: string;
  userId: string;
  title: string;
  description: string;
  totalAmount: number;
  currency: string;
  expenseDate: Date;
  category: ExpenseCategory;
  status: ExpenseStatus;
  receiptUrls: string[];
  approvalChain: ExpenseApproval[];
  createdAt: Date;
  updatedAt: Date;
  items: ExpenseItem[];
}

export interface ExpenseItem {
  id: string;
  description: string;
  amount: number;
  category: ExpenseCategory;
  date: Date;
  receiptUrl?: string;
}

export enum ExpenseCategory {
  ACCOMMODATION = 'ACCOMMODATION',
  MEALS = 'MEALS',
  TRANSPORTATION = 'TRANSPORTATION',
  ENTERTAINMENT = 'ENTERTAINMENT',
  MISCELLANEOUS = 'MISCELLANEOUS'
}

export enum ExpenseStatus {
  DRAFT = 'DRAFT',
  SUBMITTED = 'SUBMITTED',
  UNDER_REVIEW = 'UNDER_REVIEW',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  PAID = 'PAID'
}

export interface ExpenseApproval {
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
