import { useState } from 'react';

export function useAsyncAction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function run(action, successMessage) {
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const result = await action();
      if (successMessage) {
        setMessage(successMessage);
      }
      return result;
    } catch (err) {
      setError(err.status ? `${err.status}: ${err.message}` : err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }

  return { loading, error, message, run, setError, setMessage };
}
