/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the 'License');
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

@isTest
private class AgentAssistAuthControllerTest {
    private class MockOAuthSuccessResponse implements HttpCalloutMock {
        public HTTPResponse respond(HTTPRequest req) {
            HttpResponse res = new HttpResponse();
            res.setHeader('Content-Type', 'application/json');
            res.setBody('{"access_token": "mock_access_token_xyz", "token_type": "Bearer", "expires_in": 7200}');
            res.setStatusCode(200);
            return res;
        }
    }

    private class MockOAuthErrorResponse implements HttpCalloutMock {
        public HTTPResponse respond(HTTPRequest req) {
            HttpResponse res = new HttpResponse();
            res.setHeader('Content-Type', 'application/json');
            res.setBody('{"error": "invalid_client", "error_description": "client authentication failed"}');
            res.setStatusCode(400);
            res.setStatus('Bad Request');
            return res;
        }
    }

    @isTest
    static void testGetOAuthTokenSuccess() {
        Test.setMock(HttpCalloutMock.class, new MockOAuthSuccessResponse());

        Test.startTest();
        String token = AgentAssistAuthController.getOAuthToken('mockKey', 'mockSecret');
        Test.stopTest();

        System.assertEquals('mock_access_token_xyz', token, 'Should successfully return mock access token via explicit credentials');
    }

    @isTest
    static void testGetOAuthTokenFailureResponse() {
        Test.setMock(HttpCalloutMock.class, new MockOAuthErrorResponse());

        Boolean exceptionThrown = false;
        Test.startTest();
        try {
            AgentAssistAuthController.getOAuthToken('mockKey', 'mockSecret');
        } catch (AuraHandledException e) {
            exceptionThrown = true;
        }
        Test.stopTest();

        System.assert(exceptionThrown, 'Should throw AuraHandledException when OAuth callout fails');
    }

    @isTest
    static void testGetLatestInteractionIdWithTaskOnRecord() {
        Case c = new Case(Subject = 'Test Case');
        insert c;

        Task t = new Task(
            WhatId = c.Id,
            Subject = 'Call Interaction',
            CallObject = '5f3d8b60-2c3f-4acb-95ad-8a770234c18e',
            Status = 'Completed'
        );
        insert t;

        Test.startTest();
        String interactionId = AgentAssistAuthController.getLatestInteractionId(c.Id);
        Test.stopTest();

        System.assertEquals('5f3d8b60-2c3f-4acb-95ad-8a770234c18e', interactionId);
    }

    @isTest
    static void testGetLatestInteractionIdForUser() {
        Task t = new Task(
            Subject = 'Call Interaction User',
            CallObject = 'cd7c1661-39fa-477b-ac98-ff1d0ce872d4',
            Status = 'Completed'
        );
        insert t;

        Test.startTest();
        String interactionId = AgentAssistAuthController.getLatestInteractionId(null);
        Test.stopTest();

        System.assertEquals('cd7c1661-39fa-477b-ac98-ff1d0ce872d4', interactionId);
    }

    @isTest
    static void testGetLatestInteractionIdNoTasks() {
        Test.startTest();
        String interactionId = AgentAssistAuthController.getLatestInteractionId(null);
        Test.stopTest();

        System.assertEquals(null, interactionId, 'Should return null when no tasks exist');
    }

    @isTest
    static void testGetLatestInteractionIdBlankCallObject() {
        Case c = new Case(Subject = 'Test Case Blank CallObject');
        insert c;

        Task t = new Task(
            WhatId = c.Id,
            Subject = 'Manual Task Without CTI',
            CallObject = null,
            Status = 'Completed'
        );
        insert t;

        Test.startTest();
        String interactionId = AgentAssistAuthController.getLatestInteractionId(c.Id);
        Test.stopTest();

        System.assertEquals(null, interactionId, 'Should ignore tasks without CallObject');
    }
}
