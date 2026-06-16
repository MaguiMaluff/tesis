import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { OverviewComponent } from './overview/overview';
import { CreateChildComponent } from '../children/create/create';
import { DetailComponent } from './detail/detail';

const routes: Routes = [
  { path: '', component: OverviewComponent },
  { path: 'new', component: CreateChildComponent },
  { path: ':id', component: DetailComponent },
];

@NgModule({
  imports: [CommonModule, RouterModule.forChild(routes), OverviewComponent, CreateChildComponent, DetailComponent],
})
export class DashboardModule {}