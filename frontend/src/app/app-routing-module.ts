import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ConversationsModule } from './features/conversations/conversations-module';
import { DashboardModule } from './features/dashboard/dashboard.service';
import { RiskCasesModule } from './features/risk-cases/risk-cases-module';
import { ListComponent as ConvListComponent } from './features/conversations/list/list';
import { DetailComponent as ConvDetailComponent } from './features/conversations/detail/detail';
import { OverviewComponent } from './features/dashboard/overview/overview';
import { ListComponent as RiskListComponent } from './features/risk-cases/list/list';
import { DetailComponent as RiskDetailComponent } from './features/risk-cases/detail/detail';

const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: OverviewComponent },
  { path: 'conversations', component: ConvListComponent },
  { path: 'conversations/:id', component: ConvDetailComponent },
  { path: 'risk-cases', component: RiskListComponent },
  { path: 'risk-cases/:id', component: RiskDetailComponent },
  { path: '**', redirectTo: '/dashboard' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes), ConversationsModule, DashboardModule, RiskCasesModule],
  exports: [RouterModule],
})
export class AppRoutingModule {}