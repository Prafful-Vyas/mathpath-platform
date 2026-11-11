import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const topics = [
  { slug: "fractions", title: "Fractions", grade: 6, order: 1, description: "Unlike denominators." },
  { slug: "exponents", title: "Laws of Exponents", grade: 8, order: 5, description: "Powers." },
];
const next = {
  problem: { id: "fractions-10", topic: "fractions", rating: 660, prompt: "Work out 1/2 + 1/4.",
    answer_type: "fraction", hint: "Use a common denominator." },
  student_rating: 800, target_rating: 653, expected_success: 0.71,
};

type Handler = (url: string, init?: RequestInit) => unknown;
let submitted: { attempt_id: string; answer: string }[];

function mockFetch(onSubmit: Handler) {
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    let body: unknown;
    if (url === "/api/content/topics") body = topics;
    else if (url.endsWith("/progress")) body = [];
    else if (url.endsWith("/next")) body = next;
    else if (url.endsWith("/attempts")) {
      submitted.push(JSON.parse(String(init?.body)));
      body = onSubmit(url, init);
    }
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
}

beforeEach(() => {
  submitted = [];
  window.history.replaceState(null, "", "/");
});

describe("App", () => {
  it("lists topics from the content service", async () => {
    mockFetch(() => ({}));
    render(<App />);
    expect(await screen.findByText("Fractions")).toBeInTheDocument();
    expect(screen.getByText("Grade 8")).toBeInTheDocument();
  });

  it("practises a problem: hint, submit, feedback with rating change", async () => {
    mockFetch(() => ({ attempt_id: "a", problem_id: "fractions-10", correct: false,
      feedback: "Right value, but simplify the fraction fully.", correct_answer: "3/4",
      rating_before: 800, rating_after: 781, mastery: "starting", replayed: false }));
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Practise Fractions" }));
    expect(await screen.findByTestId("prompt")).toHaveTextContent("1/2 + 1/4");
    await userEvent.click(screen.getByRole("button", { name: "Hint" }));
    expect(await screen.findByText("Use a common denominator.")).toBeVisible();
    await userEvent.type(screen.getByLabelText("Your answer"), "6/8");
    await userEvent.click(screen.getByRole("button", { name: "Check" }));
    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("simplify");
    expect(status).toHaveTextContent("3/4");
    expect(status).toHaveTextContent("800 → 781");
    expect(submitted).toEqual([expect.objectContaining({ answer: "6/8" })]);
    expect(submitted[0].attempt_id).toMatch(/^[0-9a-f]{32}$/);
  });

  it("deep-links into a topic from the curriculum site", async () => {
    window.history.replaceState(null, "", "/?topic=fractions");
    mockFetch(() => ({}));
    render(<App />);
    expect(await screen.findByTestId("prompt")).toHaveTextContent("1/2 + 1/4");
  });

  it("shows the service error message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 503 })));
    render(<App />);
    await waitFor(() => expect(screen.getByText("Content service is unavailable")).toBeInTheDocument());
  });
});
