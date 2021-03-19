import { makeStyles } from '@material-ui/core/styles';

export const useStyles = makeStyles((theme) => ({
  section: {
    marginBottom: "2rem"
  },
  tabList: {
    "& > div > div": {
      flexWrap: "wrap",
    },
    "& > div > span": {
      backgroundColor: theme.palette.primary.main
    },
    "& .MuiTab-root.Mui-selected, & .MuiTab-root:hover": {
      background: theme.palette.primary.light,
      "& span,svg": {
        color: theme.palette.text.primary,
      },
    }
  },
  tabPanel: {
    padding: "1rem 0 !important"
  },
  card: {
    background: theme.palette.primary.contrastText,
    width: "100%",
    "& > button": {
      padding: "1rem",
      width: "100%",
      height: "10rem",
      "& > div": {
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "row",
      }
    },
    "& span": {
      display: "block",
    },
    "& span:first-child": {
      fontWeight: "bold",
    },
    "&:hover": {
      background: theme.palette.primary.main,
      cursor: "pointer",
      color: theme.palette.text.secondary,
      "& div:first-child p": {
        color: theme.palette.primary.light,
      },
      "& a": {
        color: theme.palette.text.secondary
      }
    }
  },
  break: {
    background: "transparent",
    border: "2px solid " + theme.palette.primary.contrastText,
    "& button": {
      cursor: "default !important",
    },
    "&:hover": {
      background: "transparent",
      color: theme.palette.text.primary,
      "& div:first-child p": {
        color: theme.palette.text.primary,
      },
      "& div": {
        background: "transparent !important",
      }
    }
  },
  actionArea: {
    "&:hover $focusHighlight": {
      opacity: 0
    },
  },
  focusHighlight: {
  },
  left: {
    flex: "0 0 60%",
    "& p": {
      color: theme.palette.text.primary,
    },
  },
  right: {
    flex: "0 0 40%",
    textAlign: "right",
  },
  link: {
    color: theme.palette.text.secondary,
    marginLeft: ".5rem",
  }
}));
