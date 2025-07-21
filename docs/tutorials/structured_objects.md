# Structured Objects in PyonFX: `Meta`, `Style`, `Line`, `Word`, `Syllable`, and `Char`

ASS files are parsed by PyonFX to produce structured objects that capture the metadata, styling, and hierarchical segmentation of subtitle content. This document presents a detailed overview of these objects.

---

## Global Properties and Styling

### Meta
The `Meta` class in PyonFX contains information about the overall ASS file. Its attributes include:

- `wrap_style`: determines how line breaking is applied to the subtitle lines (corresponds to Aegisub's text wrapping behavior);
- `scaled_border_and_shadow`: indicates whether border and shadow should be scaled based on script resolution (`True`) or video resolution (`False`);
- `play_res_x` & `play_res_y`: define respectively the video’s width and height resolution, essential for determining accurate layout and positioning of the text;
- `audio`: stores the absolute path to the audio file associated with the subtitle, if any;
- `video`: stores the absolute path to the video file associated with the subtitle, or a string representing a dummy video;
- `timestamps`: holds the timing information extracted from the video file. When a valid video is provided, this attribute is populated with detailed timing info.

Each of these attributes is used during the ASS file parsing process to ensure that subtitles are rendered with the correct timing, positioning, and visual style.

**Illustration Placeholder:**

![Meta Detailed Diagram](path/to/meta-detailed-image.png)

### Style

The `Style` object encapsulates the typographic formatting rules that determine the visual appearance of subtitle text. It is modeled to mirror the standard Aegisub style definition.

Key properties include:

- `name`: the unique identifier for the style;
- `fontname`: the font used for text rendering;
- `fontsize`: the size of the font in points;
- `color1` and `alpha1`: the primary fill color and its transparency;
- `color2` and `alpha2`: the secondary (karaoke only) color and its transparency;
- `color3` and `alpha3`: the outline (border) color and its transparency;
- `color4` and `alpha4`: the shadow color and its transparency;
- `bold`, `italic`, `underline`, `strikeout`: boolean flags that indicate whether the corresponding text formatting option has been selected;
- `scale_x` and `scale_y`: horizontal and vertical scaling percentages;
- `spacing`: additional space between characters;
- `angle`: rotation angle of the text in degrees;
- `border_style`: whether to apply an opaque box (`True`) or a standard outlined border (`False`);
- `outline`: the thickness of the text outline;
- `shadow`: the offset distance for the shadow layer;
- `alignment`: an integer that follows ASS alignment codes, controlling how text is aligned on screen (for example, a value of 7 typically denotes center-bottom alignment);
- `margin_l`, `margin_r`, `margin_v`: the left, right, and vertical margins;
- `encoding`: the font encoding used for characters rendering.

![Aegisub Style Mapping](path/to/style-mapping-img.png)

---

## Subtitle Segmentation and Event Structure

### Line

The `Line` class in PyonFX provides a comprehensive representation of a single subtitle event within an ASS file. Each instance encapsulates multiple layers of information that together dictate how the subtitle is rendered:

- `comment`: indicates if the line is a comment (non-dialogue) or an actual dialogue event;
- `layering`: establishes the drawing order, with higher values appearing above lower ones;
- `start_time`, `end_time`: determine respectively the appearance and disappearance time (in milliseconds) of the line;
- `style` & `styleref`: hold respectively the style name and a reference to the corresponding Style object;
- `actor` & `effect`: denote respectively the speaker, useful in dialogues involving multiple characters;
- `margin_l`, `margin_r`, `margin_v`: supersede respectively the left, right and vertical margins defined in the `styleref` object;
- `actor` and `effect`: hold the 2 strings assigned to the respective fields;
- `raw_text`: stores the original text (including formatting tags).

What we listed is how the original .ass lines information are stored. Beyond the basic ASS event data, the `Line` object in PyonFX is enriched with additional attributes that are actually essential to do anything meaningful with the library:

- `text`: the stripped version of the line’s text, free from ASS formatting tags;
- `i`: a unique index indicating the line’s position in the parsed file;
- `duration`: the display duration (in milliseconds), computed as `end_time - start_time`;
- `leadin` & `leadout`: time gaps (in milliseconds) respectively before the line starts (compared to the previous line) and after it ends (before the next line);
- `width` & `height`: the calculated dimensions (in pixels) of the rendered text, based on font metrics;
- `ascent`, `descent`, `internal_leading` & `external_leading`: detailed font metrics used to achieve precise vertical alignment.
- `x` & `y`: the computed horizontal and vertical positions on screen, derived from alignment rules and margin settings;
- `left`, `center`, and `right`: horizontal boundaries and center point;
- `top`, `middle`, and `bottom`: vertical boundaries and middle point;
- `words`: a list of `Word` objects (see later section);
- `syls`: a list of `Syllable` objects (see later section);
- `chars`: a list of `Char` objects (see later section);
