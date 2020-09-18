import { makeStyles } from '@material-ui/core/styles';

export const useStyles = makeStyles((theme) => ({
  sidebarIframe: {
    border: "none",
    width: "100%",
    height: "100%",
    "& iframe": {
      border: "none",
    }
  },
  bbbIframe: {
    height: "calc(100% - 2rem)",
    background: theme.palette.primary.contrastText,
    borderRadius: ".3rem",
    "& iframe": {
      border: "none",
      padding: ".5rem",
    }
  },
  resultsIframe: {
    height: "calc(100% - 2rem)",
    background: theme.palette.primary.contrastText,
    borderRadius: ".3rem",
    "& iframe": {
      border: "none",
      padding: ".5rem",
    }
  },
}));
