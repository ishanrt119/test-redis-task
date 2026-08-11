import { Component } from '@angular/core';
import { DemoService } from './demo.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  message = 'Click Home or Contact';

  constructor(private demo: DemoService) {}

  loadHome() {
    this.demo.getHome().subscribe(res => {
      this.message = res.message;
    });
  }

  loadContact() {
    this.demo.getContact().subscribe(res => {
      this.message = res.message;
    });
  }
}
