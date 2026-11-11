import { Alert, AppBar, Box, Container, Tab, Tabs, TextField, Toolbar, Typography } from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { Topic, TopicProgress, api } from "./api";
import { PracticePanel } from "./components/PracticePanel";
import { ProgressTable } from "./components/ProgressTable";
import { TopicGrid } from "./components/TopicGrid";

function initialStudent(): string {
  const fromUrl = new URLSearchParams(window.location.search).get("student");
  try {
    return fromUrl ?? localStorage.getItem("mathpath.student") ?? "demo-student";
  } catch {
    return fromUrl ?? "demo-student";
  }
}

export default function App() {
  const [studentId, setStudentId] = useState(initialStudent);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [progress, setProgress] = useState<TopicProgress[]>([]);
  const [active, setActive] = useState<Topic | null>(null);
  const [tab, setTab] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.topics().then((ts) => {
      setTopics(ts);
      // Deep link from the Gatsby curriculum site: /?topic=fractions
      const wanted = new URLSearchParams(window.location.search).get("topic");
      setActive(ts.find((t) => t.slug === wanted) ?? null);
    }).catch(() => setError("Content service is unavailable"));
  }, []);

  const refreshProgress = useCallback(() => {
    api.progress(studentId).then(setProgress).catch(() => setProgress([]));
  }, [studentId]);

  useEffect(() => {
    refreshProgress();
    try {
      localStorage.setItem("mathpath.student", studentId);
    } catch {
      /* storage blocked: the id still works for this session */
    }
  }, [refreshProgress, studentId]);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "grey.50" }}>
      <AppBar position="static" elevation={0}>
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>MathPath</Typography>
          <TextField size="small" label="Student" value={studentId}
            onChange={(e) => setStudentId(e.target.value.replace(/[^A-Za-z0-9_-]/g, "").slice(0, 40) || "demo-student")}
            sx={{ bgcolor: "background.paper", borderRadius: 1 }} />
        </Toolbar>
      </AppBar>
      <Container sx={{ py: 3 }}>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label="Practice" />
          <Tab label="My progress" />
        </Tabs>
        {tab === 0 && (active ? (
          <PracticePanel key={`${studentId}:${active.slug}`} studentId={studentId} topic={active}
            onBack={() => setActive(null)} onAnswered={refreshProgress} />
        ) : (
          <TopicGrid topics={topics} progress={progress} onPick={setActive} />
        ))}
        {tab === 1 && <ProgressTable topics={topics} progress={progress} />}
      </Container>
    </Box>
  );
}
