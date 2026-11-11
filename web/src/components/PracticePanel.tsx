import { Alert, Box, Button, Chip, CircularProgress, Collapse, Paper, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { ApiError, AttemptResult, NextProblem, Topic, api, newAttemptId } from "../api";

interface Props {
  studentId: string;
  topic: Topic;
  onBack: () => void;
  onAnswered: () => void;
}

export function PracticePanel({ studentId, topic, onBack, onAnswered }: Props) {
  const [current, setCurrent] = useState<NextProblem | null>(null);
  // One attempt id per problem: a double-click or network retry re-sends the same id,
  // and the practice service replays the stored result instead of counting it twice.
  const [attemptId, setAttemptId] = useState(newAttemptId);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [busy, setBusy] = useState(false);

  const loadNext = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setCurrent(await api.next(studentId, topic.slug));
      setAttemptId(newAttemptId());
      setAnswer("");
      setResult(null);
      setShowHint(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load a problem");
    } finally {
      setBusy(false);
    }
  }, [studentId, topic.slug]);

  useEffect(() => {
    void loadNext();
  }, [loadNext]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!current || !answer.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.submit(studentId, attemptId, current.problem.id, answer));
      onAnswered();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">{topic.title}</Typography>
        <Button onClick={onBack}>All topics</Button>
      </Stack>

      {!current && busy && <CircularProgress aria-label="loading" />}
      {current && (
        <Box component="form" onSubmit={submit}>
          <Stack direction="row" spacing={1} mb={2}>
            <Chip label={`Your rating ${result ? result.rating_after : current.student_rating}`} color="primary" />
            <Chip label={`Problem ${current.problem.rating}`} variant="outlined" />
          </Stack>
          <Typography variant="h6" component="p" mb={2} data-testid="prompt">
            {current.problem.prompt}
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="flex-start">
            <TextField label="Your answer" value={answer} onChange={(e) => setAnswer(e.target.value)}
              disabled={!!result} autoFocus size="small" sx={{ minWidth: 240 }}
              helperText={current.problem.answer_type === "expression" ? "e.g. 2x^2 + 3x - 5" : " "} />
            {!result && <Button type="submit" variant="contained" disabled={busy || !answer.trim()}>Check</Button>}
            {!result && current.problem.hint && <Button onClick={() => setShowHint(true)}>Hint</Button>}
            {result && <Button variant="contained" onClick={() => void loadNext()} disabled={busy}>Next problem</Button>}
          </Stack>
          <Collapse in={showHint && !result}>
            <Alert severity="info" sx={{ mt: 2 }}>{current.problem.hint}</Alert>
          </Collapse>
        </Box>
      )}

      {result && (
        <Alert severity={result.correct ? "success" : "warning"} sx={{ mt: 2 }} role="status">
          {result.feedback}
          {result.correct_answer && <> The answer is <strong>{result.correct_answer}</strong>.</>}{" "}
          Rating {result.rating_before} → {result.rating_after} ({result.mastery}).
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
    </Paper>
  );
}
