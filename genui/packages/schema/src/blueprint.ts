// The Environment Blueprint (V5-D18): the plan written before any page code. Spec: refdocs/v5-design/docs/blueprint.md.
// It is checked deterministically (api/blueprint, rules BP-001 to BP-010) before the writer starts. It is a draft of intent,
// never something the client runs: it carries no code.
//
// Every field the wire needs is typed here once (hard constraint 7). Only constructs the codegen supports are used.

/** How a student works a changed variable with their hands. The keyboard fallback is implicit for every gesture and is never listed. */
export type Gesture = "drag" | "drop" | "rotate" | "pour" | "press-hold" | "pinch";

/** `changed`: the student changes it. `measured`: the Environment shows it. `fixed`: a constant of the setup. */
export type VariableRole = "changed" | "measured" | "fixed";

export interface BlueprintVariable {
  /** The name other fields refer to, for example `mass`. Letters, digits and underscores. */
  name: string;
  /** The unit, for example `N/m`, or an empty string for a pure number. */
  unit: string;
  min: number;
  max: number;
  role: VariableRole;
}

/** For one student-changed variable: the object they touch, how, where, and what moves in answer. */
export interface BlueprintInteraction {
  /** The name of a variable whose role is `changed`. */
  variable: string;
  /** A drawn object the student touches, for example `the mass tray`. */
  object: string;
  gesture: Gesture;
  /** Where the gesture ends or acts, for example `the hanger under the spring`. */
  target: string;
  /** The motion that answers, for example `the spring stretches as the mass settles`. */
  response: string;
}

/** The bench layout. The shares are fractions from 0 to 1 of the bench's width and height (V5-D23). */
export interface BlueprintScene {
  /** The main apparatus, for example `two springs hanging from a bar`. */
  apparatus: string;
  widthShare: number;
  heightShare: number;
  /** What fills the rest of the bench: a scale, an axis, a reference object, a backdrop element. */
  fills: string[];
  /** How a wide screen is used. */
  wideScreen: string;
}

/**
 * A statement the checker can test. `rises-with`, `falls-with` and `independent-of` relate `measured` to `variable`.
 * `stays-within` bounds `measured` between `low` and `high` over the whole sweep. `equals-at` says `measured` equals `value`
 * when `variable` is `at`.
 */
export type BehaviourKind = "rises-with" | "falls-with" | "independent-of" | "stays-within" | "equals-at";

export interface BlueprintBehaviour {
  kind: BehaviourKind;
  /** A variable whose role is `measured`. */
  measured: string;
  /** The variable swept. Empty for `stays-within`, which holds over every sweep. */
  variable: string;
  low: number | null;
  high: number | null;
  at: number | null;
  value: number | null;
  /** The statement in the student's words, for example `extension rises as the load rises`. */
  text: string;
}

/** Something the writer may use. `none` is not listed: an empty `assists` list means everything is written from scratch (V5-D16). */
export interface BlueprintAssist {
  kind: "kit-part" | "stored-environment" | "saved-part";
  /** A Kit manifest name, a stored Environment id, or a saved part id. */
  id: string;
}

export interface BlueprintPredict {
  question: string;
  choices: string[];
  /** What to do to check the prediction. */
  check: string;
}

export interface Blueprint {
  /** The science idea in one sentence, at the student's level. */
  concept: string;
  /** What the student should discover by using the Environment. */
  goal: string;
  /** What is simulated: objects, what moves, what changes. */
  phenomenon: string;
  variables: BlueprintVariable[];
  interactions: BlueprintInteraction[];
  scene: BlueprintScene;
  /** What animates, and what it shows. Still under reduced motion. */
  motion: string;
  /** The laws or rules: Kit model ids where one fits, otherwise formulas, otherwise a description of model code. */
  science: string[];
  expectedBehaviour: BlueprintBehaviour[];
  assists: BlueprintAssist[];
  predict: BlueprintPredict;
  /** Three or four steps, each naming what to drag or drop and what to watch. */
  steps: string[];
}
