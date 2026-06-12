import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(false);
  isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

  constructor() {
    // TODO: implement auth logic (check localStorage, verify token, etc)
  }

  login(email: string, password: string): Observable<any> {
    // TODO: call API
    return new Observable();
  }

  logout(): void {
    this.isAuthenticatedSubject.next(false);
  }
}