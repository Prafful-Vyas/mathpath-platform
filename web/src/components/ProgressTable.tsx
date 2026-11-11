import { LinearProgress, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import type { Topic, TopicProgress } from "../api";

// Rating 500 -> 0%, 1200 -> 100% of the bar; mastery labels come from the service.
const pct = (rating: number) => Math.min(100, Math.max(0, ((rating - 500) / 700) * 100));

export function ProgressTable({ topics, progress }: { topics: Topic[]; progress: TopicProgress[] }) {
  if (!progress.length) {
    return <Typography color="text.secondary">No attempts yet. Pick a topic to start practising.</Typography>;
  }
  const title = new Map(topics.map((t) => [t.slug, t.title]));
  return (
    <Table size="small" aria-label="progress">
      <TableHead>
        <TableRow>
          <TableCell>Topic</TableCell>
          <TableCell>Mastery</TableCell>
          <TableCell align="right">Rating</TableCell>
          <TableCell align="right">Accuracy</TableCell>
          <TableCell align="right">Attempts</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {progress.map((p) => (
          <TableRow key={p.topic}>
            <TableCell>{title.get(p.topic) ?? p.topic}</TableCell>
            <TableCell sx={{ minWidth: 160 }}>
              {p.mastery}
              <LinearProgress variant="determinate" value={pct(p.rating)} sx={{ mt: 0.5 }} />
            </TableCell>
            <TableCell align="right">{p.rating}</TableCell>
            <TableCell align="right">{Math.round(p.accuracy * 100)}%</TableCell>
            <TableCell align="right">{p.attempts}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
