import { Card, CardActionArea, CardContent, Chip, Grid2 as Grid, Stack, Typography } from "@mui/material";

import type { Topic, TopicProgress } from "../api";

interface Props {
  topics: Topic[];
  progress: TopicProgress[];
  onPick: (topic: Topic) => void;
}

export function TopicGrid({ topics, progress, onPick }: Props) {
  const bySlug = new Map(progress.map((p) => [p.topic, p]));
  return (
    <Grid container spacing={2}>
      {topics.map((t) => {
        const p = bySlug.get(t.slug);
        return (
          <Grid key={t.slug} size={{ xs: 12, sm: 6, md: 4 }}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              <CardActionArea onClick={() => onPick(t)} sx={{ height: "100%" }} aria-label={`Practise ${t.title}`}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="h6">{t.title}</Typography>
                    <Chip size="small" label={`Grade ${t.grade}`} />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {t.description}
                  </Typography>
                  {p && (
                    <Chip sx={{ mt: 1.5 }} size="small" color="primary" variant="outlined"
                      label={`${p.mastery} · ${p.attempts} attempts`} />
                  )}
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
}
