# Reviewer return format

- Exact model/provider/effort and baseline manifest SHA-256.
- Scope read; limitations or unavailable evidence.
- Up to five findings: severity, confidence (proven/supported/hypothesis),
  source file/line or evidence path, concrete trigger, actual vs expected,
  impact, smallest plausible correction, and falsifying test.
- Tests actually run: exact check/command, exit code, result, evidence output.
  A source read is not a test; a proposed test is not a passing test.
- At most one requested additional experiment: hypothesis, inputs, single
  variable, expected discrimination, command outline, duration and stop rules.
- Remaining uncertainties and recommended next integration step.
- Final summary ≤300 words. Longer test data goes in referenced artifacts.

No implementation merging, source changes, model substitution, runtime WORLD
guidance, unsupported six-destination claims or hidden test failures.
