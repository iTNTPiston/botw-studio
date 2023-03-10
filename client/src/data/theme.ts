import { Base16Theme, createStyling, Theme } from "react-base16-styling";

export const DefaultTheme: Base16Theme = {
	scheme: "Default Theme",
	author: "iTNTPiston",
	base00: "rgb(255, 255, 255)",
	base01: "rgb(245, 245, 245)",
	base02: "transparent",
	base03: "transparent",
	base04: "transparent",
	base05: "transparent",
	base06: "transparent",
	base07: "#002b36", // foreground
	base08: "transparent",
	base09: "#cb4b16", // used for loading spinners
	base0A: "transparent",
	base0B: "transparent",
	base0C: "transparent",
	base0D: "transparent",
	base0E: "transparent",
	base0F: "transparent"
};

const getWidgetDivStyleFromBase16Theme = (theme: Base16Theme) => {
	return {
		basic:{
			backgroundColor: theme.base00,
			color: theme.base07
		},
		callout: {
			backgroundColor: theme.base09,
			color: theme.base00
		},
		loading: {
			color: theme.base09
		}
	};
};

const getStylingFunctionFromTheme = (theme: Theme | undefined) => {
	if (!theme){
		theme = DefaultTheme;
	}
	return createStyling(getWidgetDivStyleFromBase16Theme, { defaultBase16: DefaultTheme })(theme);
};

type Style = {
	style: React.CSSProperties
}

export const getWidgetStylePropsFromTheme = (theme: Theme | undefined) => {
	return getStylingFunctionFromTheme(theme)("basic") as Style;
};

export const getCalloutStylePropsFromTheme = (theme: Theme | undefined) => {
	return getStylingFunctionFromTheme(theme)("callout") as Style;
};

export const getLoadingStylePropsFromTheme = (theme: Theme | undefined) => {
	return getStylingFunctionFromTheme(theme)("loading") as Style;
};

export const ThemeOptions = [
	["Default", undefined],
	["Monokai", "monokai"],
	["Ocean", "ocean"],
	["Solarized", "solarized"],
	["Mocha", "mocha"],
	["Green", "greenscreen"],
	["Light", "bright:inverted"]
] as const;

export const isDarkTheme = (theme: Theme | undefined): boolean => {
	return theme !== undefined && theme !== "bright:inverted";
}