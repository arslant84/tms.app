import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../../core/services/auth.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { Observable, map } from 'rxjs';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent implements OnInit {
  loginForm!: FormGroup;
  isSubmitting = false;
  errorMessage = '';
  applicationName$: Observable<string>;

  constructor(
    private formBuilder: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private appSettingsService: AppSettingsService
  ) {
    this.applicationName$ = this.appSettingsService.settings$.pipe(
      map(settings => settings.application_name || 'TMS')
    );
  }

  ngOnInit(): void {
    this.loginForm = this.formBuilder.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });
  }
  
  // Fill the form with test admin credentials
  fillTestCredentials(): void {
    this.loginForm.patchValue({
      email: 'turkzuk@gmail.com',
      password: 'admin'
    });
  }

  onSubmit(): void {
    // Mark all form controls as touched to trigger validation messages
    if (this.loginForm.invalid) {
      Object.keys(this.loginForm.controls).forEach(key => {
        const control = this.loginForm.get(key);
        control?.markAsTouched();
      });
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    const { email, password } = this.loginForm.value;

    console.log('Submitting login form:', { email });

    this.authService.login(email, password).subscribe({
      next: (user) => {
        console.log('Login successful, navigating to dashboard');
        this.router.navigate(['/dashboard']);
      },
      error: (error) => {
        console.error('Login error:', error);
        this.isSubmitting = false;
        
        if (error.status === 401) {
          this.errorMessage = 'Invalid email or password. Please try again.';
        } else if (error.status === 0) {
          this.errorMessage = 'Cannot connect to the server. Please check if the backend is running.';
        } else {
          this.errorMessage = error.message || 'Login failed. Please check your credentials.';
        }
      }
    });
  }
}
