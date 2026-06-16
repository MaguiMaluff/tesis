import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ConversationsModule } from './features/conversations/conversations-module';
import { DashboardModule } from './features/dashboard/dashboard-module';
import { RiskCasesModule } from './features/risk-cases/risk-cases-module';

const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', loadChildren: () => import('./features/dashboard/dashboard-module').then(m => m.DashboardModule) },
  { path: 'conversations', loadChildren: () => import('./features/conversations/conversations-module').then(m => m.ConversationsModule) },
  { path: 'risk-cases', loadChildren: () => import('./features/risk-cases/risk-cases-module').then(m => m.RiskCasesModule) },
  { path: '**', redirectTo: '/dashboard' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}