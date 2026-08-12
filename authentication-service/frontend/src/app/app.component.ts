import { Component } from '@angular/core';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  username = '';
  password = '';
  usernameError = '';
  passwordError = '';
  message = '';
  isLoggedIn = false;
  loggedInUser = '';

  constructor(private authService: AuthService) {}

  submitLogin(): void {
    this.usernameError = '';
    this.passwordError = '';
    this.message = '';

    if (!this.username.trim()) {
      this.usernameError = 'Username is required';
    }

    if (!this.password.trim()) {
      this.passwordError = 'Password is required';
    }

    if (this.usernameError || this.passwordError) {
      return;
    }

    this.authService.login(this.username.trim(), this.password).subscribe({
      next: (response) => {
        if (response.success) {
          const safeUsername = response.username ?? '';
          this.isLoggedIn = true;
          this.loggedInUser = safeUsername;
          this.message = 'Login successful';
          return;
        }

        this.isLoggedIn = false;
        this.loggedInUser = '';
        this.message = response.message || 'Invalid username or password';
      },
      error: (error) => {
        this.isLoggedIn = false;
        this.loggedInUser = '';

        if (error?.status === 401 || error?.status === 400) {
          this.message = error?.error?.message || 'Invalid username or password';
          return;
        }

        this.message = 'Unable to connect to authentication service';
      }
    });
  }

  logout(): void {
    this.isLoggedIn = false;
    this.loggedInUser = '';
    this.username = '';
    this.password = '';
    this.usernameError = '';
    this.passwordError = '';
    this.message = '';
  }
}
