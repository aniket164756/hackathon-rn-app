/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import IBLButton from './IBL-Button.component';

test('renders correctly', async () => {
  await ReactTestRenderer.act(() => {
    ReactTestRenderer.create(
      <IBLButton buttonText="Submit" onPress={() => {}} />,
    );
  });
});
