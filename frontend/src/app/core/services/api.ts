import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getConversations(): Observable<any> {
    return this.http.get(`${this.apiUrl}/conversations`);
  }

  getConversation(id: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/conversations/${id}`);
  }

  getRiskCases(): Observable<any> {
    return this.http.get(`${this.apiUrl}/risk-cases`);
  }

  getRiskCase(id: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/risk-cases/${id}`);
  }

  getPreprocessRuns(convId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/conversations/${convId}/preprocess-runs`);
  }
}