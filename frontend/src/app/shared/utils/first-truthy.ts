/**
 * First truthy value in `values`, or `fallback` if none - equivalent to
 * chaining `a || b || c || fallback` but pulls the decision points out of
 * the caller so its own cyclomatic complexity doesn't grow with every
 * fallback field added (common in backend<->frontend field-name-fallback
 * transforms, e.g. `data.request_number || data.requestNumber || ''`) -
 * and, since the fallback is baked into one function call, the caller
 * doesn't need a trailing `?? fallback` either.
 */
export function firstTruthy<T>(
  fallback: T,
  ...values: Array<T | null | undefined | false | ''>
): T {
  const found = values.find(v => !!v);
  return found !== undefined ? (found as T) : fallback;
}
