/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export enum FlexAction {
  AcceptTask = 'AcceptTask',
  ApplyTeamsViewFilters = 'ApplyTeamsViewFilters',
  CompleteTask = 'CompleteTask',
  HangupCall = 'HangupCall',
  HoldCall = 'HoldCall',
  UnholdCall = 'UnholdCall',
  HoldParticipant = 'HoldParticipant',
  KickParticipant = 'KickParticipant',
  MonitorCall = 'MonitorCall',
  StopMonitoringCall = 'StopMonitoringCall',
  SelectTask = 'SelectTask',
  SetWorkerActivity = 'SetWorkerActivity',
  StartOutboundCall = 'StartOutboundCall',
  ToggleMute = 'ToggleMute',
  UnholdParticipant = 'UnholdParticipant',
  NavigateToView = 'NavigateToView',
  RejectTask = 'RejectTask',
  SetActivity = 'SetActivity',
  StartExternalWarmTransfer = 'StartExternalWarmTransfer',
  ShowDirectory = 'ShowDirectory',
  TransferTask = 'TransferTask',
  WrapupTask = 'WrapupTask',
  LogOn = 'Logon',
}

export enum FlexActionEvent {
  before = 'before',
  after = 'after',
  replace = 'replace',
}
