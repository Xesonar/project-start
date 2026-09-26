import { describe, it } from "node:test";
import assert from "node:assert/strict";

import type { SkillLevel } from "@/api/users";
import { computeMatch, verdictFor } from "./match.ts";

// Fixture builders — keep the skill/level noise out of the assertions.
const skill = (id: number, name: string, level: SkillLevel = "beginner") =>
  ({ skill: { id, name, category: "dev" }, level });
const req = (id: number, name: string, required_level: SkillLevel) =>
  ({ skill: { id, name, category: "dev" }, required_level });

describe("computeMatch", () => {
  it("scores 100% when every required skill is covered at level", () => {
    const result = computeMatch(
      [req(1, "React", "beginner"), req(2, "Figma", "beginner")],
      [
        { ...skill(1, "React"), level: "intermediate" },
        { ...skill(2, "Figma"), level: "beginner" },
      ],
    );
    assert.equal(result.score, 1);
    assert.equal(result.covered, 2);
    assert.deepEqual(result.gaps, []);
  });

  it("marks unknown skills as gaps and scores them 0", () => {
    const result = computeMatch(
      [req(1, "React", "beginner"), req(2, "SQL", "beginner")],
      [{ ...skill(1, "React"), level: "beginner" }],
    );
    assert.equal(result.score, 0.5);
    assert.equal(result.covered, 1);
    assert.deepEqual(result.gaps, [{ name: "SQL", required_level: "beginner", status: "missing" }]);
  });

  it("gives half credit for a skill held below the required level", () => {
    const result = computeMatch(
      [req(1, "Python", "advanced")],
      [{ ...skill(1, "Python"), level: "beginner" }],
    );
    // "knows it, must level up" is worth something — the copy depends on it.
    assert.equal(result.score, 0.5);
    assert.deepEqual(result.gaps, [{ name: "Python", required_level: "advanced", status: "level" }]);
  });

  it("ignores unrelated user skills", () => {
    const result = computeMatch(
      [req(1, "React", "beginner")],
      [{ ...skill(99, "Russian language"), level: "advanced" }],
    );
    assert.equal(result.score, 0);
    assert.equal(result.gaps.length, 1);
  });

  it("treats a project with no skill requirements as a full match", () => {
    assert.equal(computeMatch([], [{ ...skill(1, "React"), level: "beginner" }]).score, 1);
  });
});

describe("verdictFor", () => {
  it("reports a perfect match at 1.0", () => {
    assert.equal(verdictFor(1).title, "Идеальное совпадение");
  });
  it("escalates the verdict as the score drops", () => {
    assert.equal(verdictFor(0.75).title, "Сильное совпадение");
    assert.equal(verdictFor(0.5).title, "Чуть-чуть не хватает");
    assert.equal(verdictFor(0.1).title, "Пока сложноват");
  });
});
