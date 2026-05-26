/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import IBLText from './IBL-Text.component';

test('renders correctly', async () => {
  await ReactTestRenderer.act(() => {
    ReactTestRenderer.create(<IBLText displayText="Hello" />);
  });
});
