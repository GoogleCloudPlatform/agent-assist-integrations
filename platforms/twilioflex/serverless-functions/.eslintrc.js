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

module.exports = {
  root: true,
  extends: ['twilio'],
  ignorePatterns: ['/node_modules', '/src/assets', '*.test.js'],
  rules: {
    camelcase: 'off',
    complexity: 'off',
    'import/extensions': 'off',
    'import/no-extraneous-dependencies': 'off',
    'import/no-mutable-exports': 'off',
    'import/no-unresolved': 'off',
    'import/no-unused-modules': 'off',
    'multiline-comment-style': 'off',
    'no-alert': 'off',
    'no-console': 'off',
    'no-multi-str': 'off',
    'no-use-before-define': 'off',
    'no-nested-ternary': 'off',
    'prefer-destructuring': 'off',
    'prefer-named-capture-group': 'off',
    'prefer-promise-reject-errors': 'off',
    'prettier/prettier': [
      'error',
      {
        endOfLine: 'auto',
      },
    ],
    'sonarjs/cognitive-complexity': 'off',
    'sonarjs/no-identical-functions': 'off',
    'sonarjs/no-duplicate-string': 'off',
  },
};
