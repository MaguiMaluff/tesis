import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { SignupComponent } from './features/auth/signup/signup';
import { AuthGuard } from './core/guards/auth-guard';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'signup', component: SignupComponent },
  { path: 'dashboard', canActivate: [AuthGuard], loadChildren: () => import('./features/dashboard/dashboard-module').then(m => m.DashboardModule) },
  { path: 'conversations', canActivate: [AuthGuard], loadChildren: () => import('./features/conversations/conversations-module').then(m => m.ConversationsModule) },
  { path: 'risk-cases', canActivate: [AuthGuard], loadChildren: () => import('./features/risk-cases/risk-cases-module').then(m => m.RiskCasesModule) },
  { path: '**', redirectTo: '/login' },
];