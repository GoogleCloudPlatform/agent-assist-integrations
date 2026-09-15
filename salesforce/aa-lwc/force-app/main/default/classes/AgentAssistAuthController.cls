/**
 * Copyright 2026 Google LLC
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

public with sharing class AgentAssistAuthController {
    @AuraEnabled(cacheable=false)
    public static String getOAuthToken(String consumerKey, String consumerSecret) {
        String domain = System.Url.getOrgDomainUrl().toExternalForm();
        String tokenEndpoint = domain + '/services/oauth2/token';

        HttpRequest req = new HttpRequest();
        req.setEndpoint(tokenEndpoint);
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/x-www-form-urlencoded');

        // Note: For a production deployment, passing secrets from the client is a security risk.
        // This integration uses explicit credentials for ease of configuration in POC environments.
        String body = 'grant_type=client_credentials'
            + '&client_id=' + EncodingUtil.urlEncode(consumerKey, 'UTF-8')
            + '&client_secret=' + EncodingUtil.urlEncode(consumerSecret, 'UTF-8');
        req.setBody(body);

        Http http = new Http();
        HttpResponse res = http.send(req);

        if (res.getStatusCode() == 200) {
            Map<String, Object> result = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
            return (String) result.get('access_token');
        } else {
            throw new AuraHandledException('Failed to retrieve access token: ' + res.getStatus() + ' - ' + res.getBody());
        }
    }

    @AuraEnabled(cacheable=false)
    public static String getLatestInteractionId(Id recordId) {
        try {
            // 1. Check for Task associated directly with this record
            if (recordId != null) {
                List<Task> recordTasks = [
                    SELECT Id, CallObject, Description, Subject, CreatedDate 
                    FROM Task 
                    WHERE WhatId = :recordId 
                    ORDER BY CreatedDate DESC 
                    LIMIT 5
                    WITH USER_MODE
                ];
                for (Task t : recordTasks) {
                    if (String.isNotBlank(t.CallObject)) {
                        return t.CallObject;
                    }
                }
            }

            // 2. Check for latest CTI Task for current user in the last 15 minutes
            DateTime recentCutoff = System.now().addMinutes(-15);
            List<Task> userTasks = [
                SELECT Id, CallObject, Description, Subject, CreatedDate 
                FROM Task 
                WHERE OwnerId = :UserInfo.getUserId() 
                  AND CreatedDate >= :recentCutoff 
                ORDER BY CreatedDate DESC 
                LIMIT 5
                WITH USER_MODE
            ];
            for (Task t : userTasks) {
                if (String.isNotBlank(t.CallObject)) {
                    return t.CallObject;
                }
            }
        } catch (Exception e) {
            // Gracefully handle any permission or object access exceptions
        }

        return null;
    }
}
