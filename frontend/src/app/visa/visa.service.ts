import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class VisaService {

  private apiUrl = '/api/visa/applications/';

  constructor(private http: HttpClient) { }

  create(data: any): Observable<any> {
    return this.http.post(this.apiUrl, data);
  }
}
