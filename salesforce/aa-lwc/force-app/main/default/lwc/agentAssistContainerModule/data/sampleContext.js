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

const sampleContext = `{
          "accounts": {
          "5678": {
                "accountOpenedDate": "2020-02-02",
                "current service": "starter plan 5g",
                "customerType": "Tech Savvy",
                "features": "Limited data cap, unlimited talk and text",
                "name": "John Smith",
                "packages": "Unlimited Ultimate",
                "phoneNumber": "555-555-5555",
                "planInformation": {
                  "dataCap": "Limited",
                  "internationalData": "Pay-per-use",
                  "numberOfLines": 1,
                  "price": 70,
                  "talk": "Unlimited",
                  "text": "Unlimited",
                  "type": "5G Start"
                },
                "plans": {
                  "unlimitedUltimate": {
                    "internationalData": "High Speed",
                    "numberOfLines": 1,
                    "price": "65",
                    "talk": "Unlimited",
                    "text": "Unlimited",
                    "type": "Unlimited Ultimate"
                  }
                },
                "recommendedProducts": [
                  {
                    "description": "Upgrade to our Unlimited Ultimate plan for high-speed international data, talk, and text.",
                    "perks": [
                      {
                        "includes": [ "Disney+", "Hulu", "ESPN+" ],
                        "name": "Disney Bundle",
                        "price": 0
                      }
                    ],
                    "plan": "Unlimited Ultimate at $65 per month"
                  },
                  {
                    "description": "Consider upgrading to the latest iPhone for an enhanced experience.",
                    "device": "New iPhone 15 Pro"
                  }
                ],
                "services": "Wireless",
                "timeWithUs": "5 years"
              }
          }
      },`;

export default sampleContext;
