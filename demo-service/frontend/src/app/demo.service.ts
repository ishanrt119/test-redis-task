import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable()
export class DemoService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getHome(): Observable<any> {
    return this.http.get<any>(`${this.base}/api/home/`);
  }

  getContact(): Observable<any> {
    return this.http.get<any>(`${this.base}/api/contact/`);
  }
}
