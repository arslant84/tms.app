import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { ExpenseClaim, ExpenseStatus, ExpenseCategory, ApprovalStatus, ExpenseItem } from '../models/expense.model';

@Injectable({
  providedIn: 'root'
})
export class ExpenseService {
  private mockExpenseClaims: ExpenseClaim[] = [
    {
      id: '1',
      trfId: '1',
      userId: '1',
      title: 'New York Client Meeting',
      description: 'Expenses for client meeting in New York',
      totalAmount: 850,
      currency: 'USD',
      expenseDate: new Date('2025-06-18'),
      category: ExpenseCategory.MISCELLANEOUS,
      status: ExpenseStatus.APPROVED,
      receiptUrls: ['receipt1.jpg', 'receipt2.jpg'],
      approvalChain: [
        {
          approverId: '3',
          approverName: 'Jane Smith',
          status: ApprovalStatus.APPROVED,
          comments: 'All expenses are valid',
          timestamp: new Date('2025-06-25')
        }
      ],
      createdAt: new Date('2025-06-22'),
      updatedAt: new Date('2025-06-25'),
      items: [
        {
          id: '1-1',
          description: 'Taxi from airport to hotel',
          amount: 75,
          category: ExpenseCategory.TRANSPORTATION,
          date: new Date('2025-06-15'),
          receiptUrl: 'receipt1.jpg'
        },
        {
          id: '1-2',
          description: 'Client dinner',
          amount: 250,
          category: ExpenseCategory.MEALS,
          date: new Date('2025-06-16'),
          receiptUrl: 'receipt2.jpg'
        },
        {
          id: '1-3',
          description: 'Hotel WiFi',
          amount: 25,
          category: ExpenseCategory.MISCELLANEOUS,
          date: new Date('2025-06-17'),
        },
        {
          id: '1-4',
          description: 'Taxi to airport',
          amount: 80,
          category: ExpenseCategory.TRANSPORTATION,
          date: new Date('2025-06-18'),
        },
        {
          id: '1-5',
          description: 'Business materials',
          amount: 120,
          category: ExpenseCategory.MISCELLANEOUS,
          date: new Date('2025-06-16'),
        },
        {
          id: '1-6',
          description: 'Lunch with team',
          amount: 300,
          category: ExpenseCategory.MEALS,
          date: new Date('2025-06-17'),
        }
      ]
    },
    {
      id: '2',
      userId: '1',
      title: 'Office Supplies',
      description: 'Monthly office supplies purchase',
      totalAmount: 150,
      currency: 'USD',
      expenseDate: new Date('2025-05-15'),
      category: ExpenseCategory.MISCELLANEOUS,
      status: ExpenseStatus.SUBMITTED,
      receiptUrls: ['receipt3.jpg'],
      approvalChain: [
        {
          approverId: '3',
          approverName: 'Jane Smith',
          status: ApprovalStatus.PENDING
        }
      ],
      createdAt: new Date('2025-05-16'),
      updatedAt: new Date('2025-05-16'),
      items: [
        {
          id: '2-1',
          description: 'Printer paper',
          amount: 45,
          category: ExpenseCategory.MISCELLANEOUS,
          date: new Date('2025-05-15'),
          receiptUrl: 'receipt3.jpg'
        },
        {
          id: '2-2',
          description: 'Ink cartridges',
          amount: 105,
          category: ExpenseCategory.MISCELLANEOUS,
          date: new Date('2025-05-15')
        }
      ]
    }
  ];

  constructor(private http: HttpClient) { }

  // Get all expense claims for a user
  getExpenseClaims(userId: string): Observable<ExpenseClaim[]> {
    // In a real app, this would make an API call
    return of(this.mockExpenseClaims.filter(claim => claim.userId === userId));
  }

  // Get expense claim by ID
  getExpenseClaimById(id: string): Observable<ExpenseClaim | undefined> {
    // In a real app, this would make an API call
    const claim = this.mockExpenseClaims.find(c => c.id === id);
    return of(claim);
  }

  // Create a new expense claim
  createExpenseClaim(claim: Partial<ExpenseClaim>): Observable<ExpenseClaim> {
    // In a real app, this would make an API call
    const newClaim: ExpenseClaim = {
      id: (this.mockExpenseClaims.length + 1).toString(),
      trfId: claim.trfId,
      userId: claim.userId || '',
      title: claim.title || '',
      description: claim.description || '',
      totalAmount: claim.totalAmount || 0,
      currency: claim.currency || 'USD',
      expenseDate: claim.expenseDate || new Date(),
      category: claim.category || ExpenseCategory.MISCELLANEOUS,
      status: ExpenseStatus.DRAFT,
      receiptUrls: claim.receiptUrls || [],
      approvalChain: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      items: claim.items || []
    };
    
    this.mockExpenseClaims.push(newClaim);
    return of(newClaim);
  }

  // Update an existing expense claim
  updateExpenseClaim(id: string, claim: Partial<ExpenseClaim>): Observable<ExpenseClaim | undefined> {
    // In a real app, this would make an API call
    const index = this.mockExpenseClaims.findIndex(c => c.id === id);
    if (index === -1) return of(undefined);
    
    const updatedClaim = { ...this.mockExpenseClaims[index], ...claim, updatedAt: new Date() };
    this.mockExpenseClaims[index] = updatedClaim;
    
    return of(updatedClaim);
  }

  // Submit an expense claim for approval
  submitExpenseClaim(id: string): Observable<ExpenseClaim | undefined> {
    // In a real app, this would make an API call
    const index = this.mockExpenseClaims.findIndex(c => c.id === id);
    if (index === -1) return of(undefined);
    
    const updatedClaim = { 
      ...this.mockExpenseClaims[index], 
      status: ExpenseStatus.SUBMITTED, 
      updatedAt: new Date(),
      approvalChain: [
        {
          approverId: '3',
          approverName: 'Jane Smith',
          status: ApprovalStatus.PENDING
        }
      ]
    };
    
    this.mockExpenseClaims[index] = updatedClaim;
    return of(updatedClaim);
  }

  // Add an expense item to a claim
  addExpenseItem(claimId: string, item: Partial<ExpenseItem>): Observable<ExpenseClaim | undefined> {
    // In a real app, this would make an API call
    const index = this.mockExpenseClaims.findIndex(c => c.id === claimId);
    if (index === -1) return of(undefined);
    
    const newItem: ExpenseItem = {
      id: `${claimId}-${this.mockExpenseClaims[index].items.length + 1}`,
      description: item.description || '',
      amount: item.amount || 0,
      category: item.category || ExpenseCategory.MISCELLANEOUS,
      date: item.date || new Date(),
      receiptUrl: item.receiptUrl
    };
    
    const updatedItems = [...this.mockExpenseClaims[index].items, newItem];
    const totalAmount = updatedItems.reduce((sum, item) => sum + item.amount, 0);
    
    const updatedClaim = { 
      ...this.mockExpenseClaims[index], 
      items: updatedItems,
      totalAmount,
      updatedAt: new Date() 
    };
    
    this.mockExpenseClaims[index] = updatedClaim;
    return of(updatedClaim);
  }

  // Upload a receipt for an expense claim
  uploadReceipt(file: File): Observable<string> {
    // In a real app, this would upload the file to a server
    // For demo purposes, we'll return a mock URL
    return of(`receipt-${Date.now()}.jpg`);
  }
}
