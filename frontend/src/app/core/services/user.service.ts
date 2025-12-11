import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { User, UserRole } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private mockUsers: User[] = [
    {
      id: '1',
      firstName: 'John',
      lastName: 'Doe',
      email: 'john.doe@example.com',
      role: UserRole.ADMIN,
      department: 'IT',
      employeeId: 'EMP001',
      profilePicture: 'assets/images/avatars/john-doe.jpg'
    },
    {
      id: '2',
      firstName: 'Jane',
      lastName: 'Smith',
      email: 'jane.smith@example.com',
      role: UserRole.MANAGER,
      department: 'Finance',
      employeeId: 'EMP002',
      profilePicture: 'assets/images/avatars/jane-smith.jpg'
    },
    {
      id: '3',
      firstName: 'Bob',
      lastName: 'Johnson',
      email: 'bob.johnson@example.com',
      role: UserRole.EMPLOYEE,
      department: 'Marketing',
      employeeId: 'EMP003',
      profilePicture: 'assets/images/avatars/bob-johnson.jpg'
    },
    {
      id: '4',
      firstName: 'Alice',
      lastName: 'Williams',
      email: 'alice.williams@example.com',
      role: UserRole.EMPLOYEE,
      department: 'HR',
      employeeId: 'EMP004',
      profilePicture: 'assets/images/avatars/alice-williams.jpg'
    },
    {
      id: '5',
      firstName: 'Charlie',
      lastName: 'Brown',
      email: 'charlie.brown@example.com',
      role: UserRole.MANAGER,
      department: 'Operations',
      employeeId: 'EMP005',
      profilePicture: 'assets/images/avatars/charlie-brown.jpg'
    }
  ];

  constructor(private http: HttpClient) { }

  // Get all users
  getAllUsers(): Observable<User[]> {
    // In a real app, this would make an API call
    return of(this.mockUsers);
  }

  // Get user by ID
  getUserById(id: string): Observable<User | undefined> {
    // In a real app, this would make an API call
    const user = this.mockUsers.find(u => u.id === id);
    return of(user);
  }

  // Get users by role
  getUsersByRole(role: UserRole): Observable<User[]> {
    // In a real app, this would make an API call
    return of(this.mockUsers.filter(u => u.role === role));
  }

  // Get users by department
  getUsersByDepartment(department: string): Observable<User[]> {
    // In a real app, this would make an API call
    return of(this.mockUsers.filter(u => u.department === department));
  }

  // Create a new user
  createUser(user: Partial<User>): Observable<User> {
    // In a real app, this would make an API call
    const newUser: User = {
      id: (this.mockUsers.length + 1).toString(),
      firstName: user.firstName || '',
      lastName: user.lastName || '',
      email: user.email || '',
      role: user.role || UserRole.EMPLOYEE,
      department: user.department || '',
      employeeId: `EMP${(this.mockUsers.length + 1).toString().padStart(3, '0')}`,
      profilePicture: user.profilePicture
    };
    
    this.mockUsers.push(newUser);
    return of(newUser);
  }

  // Update an existing user
  updateUser(id: string, user: Partial<User>): Observable<User | undefined> {
    // In a real app, this would make an API call
    const index = this.mockUsers.findIndex(u => u.id === id);
    if (index === -1) return of(undefined);
    
    const updatedUser = { ...this.mockUsers[index], ...user };
    this.mockUsers[index] = updatedUser;
    
    return of(updatedUser);
  }

  // Delete a user
  deleteUser(id: string): Observable<boolean> {
    // In a real app, this would make an API call
    const index = this.mockUsers.findIndex(u => u.id === id);
    if (index === -1) return of(false);
    
    this.mockUsers.splice(index, 1);
    return of(true);
  }

  // Update user profile picture
  updateProfilePicture(id: string, imageUrl: string): Observable<User | undefined> {
    // In a real app, this would make an API call
    const index = this.mockUsers.findIndex(u => u.id === id);
    if (index === -1) return of(undefined);
    
    const updatedUser = { ...this.mockUsers[index], profilePicture: imageUrl };
    this.mockUsers[index] = updatedUser;
    
    return of(updatedUser);
  }

  // Change user role
  changeUserRole(id: string, role: UserRole): Observable<User | undefined> {
    // In a real app, this would make an API call
    const index = this.mockUsers.findIndex(u => u.id === id);
    if (index === -1) return of(undefined);
    
    const updatedUser = { ...this.mockUsers[index], role };
    this.mockUsers[index] = updatedUser;
    
    return of(updatedUser);
  }
}
