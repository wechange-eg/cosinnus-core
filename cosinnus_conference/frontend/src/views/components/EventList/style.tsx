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
    }
  },
  tabPanel: {
    padding: "1rem 0 !important"
  },
  list: {
    "& li": {
      "&:first-child": {
        background: "transparent",
        padding: 0,
        "& span": {
          fontWeight: 700,
          textTransform: "uppercase"
        },
      }
    },
    "& > div": {
      background: theme.palette.background.paper,
      minHeight: "3rem",
      borderRadius: ".3rem",
      marginBottom: "1rem",
      padding: 0,
      "& div.room-title": {
        "& span, & p": {
          fontWeight: 700,
          color: theme.palette.text.primary,
          wordBreak: "break-word",
        }
      },
      "& div.event-title": {
        "& span:first-child": {
          fontWeight: 700,
          lineHeight: "1.3",
        },
        "& span:last-child, span:last-child *": {
          background: "transparent",
          color: theme.palette.text.primary,
          padding: 0,
          lineHeight: "1.3",
        }
      },
      "&:hover": {
        background: theme.palette.primary.main,
        "& div.room-title": {
          "& span, & p": {
            color: theme.palette.text.secondary
          }
        },
        "& div.event-title": {
          "& span:first-child": {
            color: theme.palette.text.secondary
          },
          "& span:last-child, span:last-child *": {
            color: theme.palette.text.secondary,
          }
        },
        "& a": {
          color: theme.palette.text.secondary
        }
      },
      [theme.breakpoints.down('sm')]: {
        height: "auto",
        padding: "1rem",
      },
    },
    "& > li, & > div": {
      [theme.breakpoints.down('sm')]: {
        flexWrap: "wrap",
      },
      "& div:first-child": {
        flexBasis: "20%",
        "& span, & p": {
          textAlign: "right",
          textTransform: "uppercase",
          fontWeight: 700,
          paddingRight: "1.5rem",
          [theme.breakpoints.down('sm')]: {
            textAlign: "left",
          },
        },
        [theme.breakpoints.down('sm')]: {
          flexBasis: "100%",
        },
      },
      "& div": {
        flexBasis: "80%",
        margin: "0.2rem",
        [theme.breakpoints.down('sm')]: {
          flexBasis: "100%",
        },
      },
    },
    "&.now > div": {
      background: theme.palette.primary.contrastText,
    },
  },
  classes: {
    padding: "0 2rem 0 0"
  }
}))
