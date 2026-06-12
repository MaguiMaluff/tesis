import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { OverviewComponent } from './overview/overview';

const routes: Routes = [
  { path: '', component: OverviewComponent },
];

@NgModule({
  imports: [CommonModule, RouterModule.forChild(routes), OverviewComponent],
})
export class DashboardModule {}