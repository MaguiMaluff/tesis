import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ListComponent } from './list/list';
import { DetailComponent } from './detail/detail';

@NgModule({
  declarations: [ListComponent, DetailComponent],
  imports: [CommonModule, RouterModule],
})
export class ConversationsModule {}