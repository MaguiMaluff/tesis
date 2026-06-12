import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { OverviewComponent } from './overview/overview';

@NgModule({
  declarations: [OverviewComponent],
  imports: [CommonModule, RouterModule],
})
export class DashboardModule {}