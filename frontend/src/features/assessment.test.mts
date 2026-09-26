import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  ANSWER_OPTIONS,
  ROLE_QUESTIONS,
  ROLES,
  answersToExperienceLevel,
  ratingToSkillLevel,
} from "./assessment.ts";

describe("assessment configuration", () => {
  it("has six roles, five questions per role and five answer options", () => {
    assert.equal(ROLES.length, 6);
    assert.equal(ANSWER_OPTIONS.length, 5);
    for (const role of ROLES) assert.equal(ROLE_QUESTIONS[role].length, 5);
  });

  it("maps self-assessment ratings to measurable levels", () => {
    assert.equal(ratingToSkillLevel(2), "beginner");
    assert.equal(ratingToSkillLevel(3), "intermediate");
    assert.equal(ratingToSkillLevel(4), "advanced");
    assert.equal(answersToExperienceLevel([4, 4, 3, 4, 3]), "advanced");
  });
});
