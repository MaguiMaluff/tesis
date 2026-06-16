import { Routes } from '@angular/router';
import { OverviewComponent } from './features/dashboard/overview/overview';
import { ListComponent as ConvListComponent } from './features/conversations/list/list';
import { DetailComponent as ConvDetailComponent } from './features/conversations/detail/detail';
import { ListComponent as RiskListComponent } from './features/risk-cases/list/list';
import { DetailComponent as RiskDetailComponent } from './features/risk-cases/detail/detail';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: OverviewComponent },
  { path: 'conversations', component: ConvListComponent },
  { path: 'conversations/:id', component: ConvDetailComponent },
  { path: 'risk-cases', component: RiskListComponent },
  { path: 'risk-cases/:id', component: RiskDetailComponent },
  { path: '**', redirectTo: 'dashboard' },
];