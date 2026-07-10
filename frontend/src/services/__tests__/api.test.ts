import { describe, it, expect } from 'vitest';
import { api } from '../api';

describe('api service', () => {
  it('has navigate method', () => {
    expect(typeof api.navigate).toBe('function');
  });
});
