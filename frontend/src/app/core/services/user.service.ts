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
      id: 1,
      name: 'John Doe',
      firstName: 'John',
      lastName: 'Doe',
      email: 'john.doe@example.com',
      role: UserRole.ADMIN,
      department: 'IT',
      is_admin: true,
      is_active: true,
      staff_id: 'EMP001',
      avatar: 'assets/images/avatars/john-doe.jpg'
    },
    {
      id: 2,
      name: 'Jane Smith',
      firstName: 'Jane',
      lastName: 'Smith',
      email: 'jane.smith@example.com',
      role: UserRole.HOD,
      department: 'Finance',
      is_admin: false,
      is_active: true,
      staff_id: 'EMP002',
      avatar: 'assets/images/avatars/jane-smith.jpg'
    },
    {
      id: 3,
      name: 'Bob Johnson',
      firstName: 'Bob',
      lastName: 'Johnson',
      email: 'bob.johnson@example.com',
      role: UserRole.EMPLOYEE,
      department: 'Marketing',
      is_admin: false,
      is_active: true,
      staff_id: 'EMP003',
      avatar: 'assets/images/avatars/bob-johnson.jpg'
    },
    {
      id: 4,
      name: 'Alice Williams',
      firstName: 'Alice',
      lastName: 'Williams',
      email: 'alice.williams@example.com',
      role: UserRole.EMPLOYEE,
      department: 'HR',
      is_admin: false,
      is_active: true,
      staff_id: 'EMP004',
      avatar: 'assets/images/avatars/alice-williams.jpg'
    },
    {
      id: 5,
      name: 'Charlie Brown',
      firstName: 'Charlie',
      lastName: 'Brown',
      email: 'charlie.brown@example.com',
      role: UserRole.HOD,
      department: 'Operations',
      is_admin: false,
      is_active: true,
      staff_id: 'EMP005',
      avatar: 'assets/images/avatars/charlie-brown.jpg'
    }
  ];

  constructor(private http: HttpClient) { }

  // Get all users
  getAllUsers(): Observable<User[]> {
    // In a real app, this would make an API call
    return of(this.mockUsers);
  }

  // Get user by ID
  getUserById(id: number): Observable<User | undefined> {
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
      id: this.mockUsers.length + 1,
      name: user.name || `${user.firstName || ''} ${user.lastName || ''}`.trim(),
      firstName: user.firstName || '',
      lastName: user.lastName || '',
      email: user.email || '',
      role: user.role || UserRole.EMPLOYEE,
      department: user.department || '',
      is_admin: user.is_admin || false,
      is_active: user.is_active !== undefined ? user.is_active : true,
      staff_id: `EMP${(this.mockUsers.length + 1).toString().padStart(3, '0')}`,
      avatar: user.avatar
    };

    this.mockUsers.push(newUser);
    return of(newUser);
  }

  // Update an existing user
  updateUser(id: number, user: Partial<User>): Observable<User | undefined> {
    // In a real app, this would make an API call
    const index = this.mockUsers.findIndex(u => u.id === id);
    if (index === -1) return of(undefined);

    const updatedUser = { ...this.mockUsers[index], ...user };
    this.mockUsers[index] = updatedUser;

    return of(updatedUser);
  }

  // Delete a user
  deleteUser(id: number): Observable<boolean> {
    // In a real app, this would make an API call
    const index = this.mockUsers.findIndex(u => u.id === id);
    if (index === -1) return of(false);

    this.mockUsers.splice(index, 1);
    return of(true);
  }

  // Update user profile picture
  updateProfilePicture(id: number, imageUrl: string): Observable<User | undefined> {
    // In a real app, this would make an API call
    const index = this.mockUsers.findIndex(u => u.id === id);
    if (index === -1) return of(undefined);

    const updatedUser = { ...this.mockUsers[index], avatar: imageUrl };
    this.mockUsers[index] = updatedUser;

    return of(updatedUser);
  }

  // Change user role
  changeUserRole(id: number, role: UserRole): Observable<User | undefined> {
    // In a real app, this would make an API call
    const index = this.mockUsers.findIndex(u => u.id === id);
    if (index === -1) return of(undefined);

    const updatedUser = { ...this.mockUsers[index], role };
    this.mockUsers[index] = updatedUser;

    return of(updatedUser);
  }
}
