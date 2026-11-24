import { describe, expect, it } from "vitest";
import { citationText, documentTitle } from "./citation";

describe("documentTitle", () => {
  it.each([
    ["textbook-physics-physics-f5-removed", "Physics textbook"],
    ["textbook-physics-physics-f4-removed", "Physics textbook"],
    ["textbook-chemistry-chemistry-f4", "Chemistry textbook"],
    ["textbook-chemistry-chemistry-f5", "Chemistry textbook"],
    ["textbook-biology-form-4-dlp-biology-f4", "Biology textbook"],
    ["textbook-biology-form-5-dlp-biology-form-5", "Biology textbook"],
  ])("%s", (id, title) => expect(documentTitle(id)).toBe(title));

  it("shows an id it does not recognise exactly as it is", () => {
    expect(documentTitle("UNVERIFIED (corpus not loaded until P2)")).toBe("UNVERIFIED (corpus not loaded until P2)");
    expect(documentTitle("notes-physics-f5")).toBe("notes-physics-f5");
  });
});

describe("citationText", () => {
  it("names the book and the PDF page", () => {
    expect(citationText({ source: "textbook-physics-physics-f5-removed", page: 36, verified: true })).toBe(
      "Physics textbook, PDF page 36",
    );
  });
  it("shows the book's own page first when it is known, and the PDF page beside it", () => {
    expect(citationText({ source: "textbook-physics-physics-f4-removed", page: 112, printedPage: 107, verified: true })).toBe(
      "Physics textbook, page 107 (PDF page 112)",
    );
  });
  it("says when a citation is not verified, and omits a missing page", () => {
    expect(citationText({ source: "UNVERIFIED (no textbook page has been checked for this Environment)", page: null, verified: false })).toBe(
      "UNVERIFIED (no textbook page has been checked for this Environment) (not verified)",
    );
  });
});
