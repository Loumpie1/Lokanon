import { measureText } from "@remotion/layout-utils";
import { fonts } from "../theme";

/** Textbreite in px, nur nach dem Laden der Schriften aufrufen. */
export const textWidth = (
  text: string,
  fontSize: number,
  fontWeight: number | string = 400,
  family: string = fonts.sansFamily,
  letterSpacing = "normal",
): number =>
  measureText({
    text,
    fontFamily: family,
    fontSize,
    fontWeight: String(fontWeight),
    letterSpacing,
    validateFontIsLoaded: true,
  }).width;
