import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { ListComponent } from './list/list';
import { DetailComponent } from './detail/detail';

const routes: Routes = [
  { path: '', component: ListComponent },
  { path: ':id', component: DetailComponent },
];

@NgModule({
  imports: [CommonModule, RouterModule.forChild(routes), ListComponent, DetailComponent],
})
export class RiskCasesModule {}