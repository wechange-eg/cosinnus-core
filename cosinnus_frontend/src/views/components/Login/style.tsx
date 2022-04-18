import React from "react"
import { Box, Button, Grid, Typography } from "@material-ui/core"
import { styled, makeStyles } from "@material-ui/core/styles"
import { Form } from "formik"
import { TextField } from "formik-material-ui"

const imgType = (<img/>).type;

export const LoginButton = styled(Button)({
  marginBottom: 8
});

export const LoginForm = styled(Form)({

});

export const LoginGrid = styled(Grid)({
  display: "flex",
  padding: 100
});

export const LoginImg = styled(imgType)({
  display: "block",
  margin: "0 auto 4rem",
  height: "3rem",
  padding: "0 4rem"
});

export const LoginOverlay = styled(Box)({
  position: "absolute",
  left: 0,
  right: 0,
  top: 0,
  bottom: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  flexDirection: "column",
  backdropFilter: "blur(5px)",
  zIndex: 1000
});

export const LoginProgressTypography = styled(Typography)({
  marginTop: 8
});

export const LoginTextField = styled(TextField)(({ theme }) => ({
  minWidth: 250,
  background: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  marginBottom: 8
}));

export const useInputPropsStyles = makeStyles(theme => ({
  underline: {
    "&&&:before": {
      borderBottom: "none"
    },
    "&&:after": {
      borderBottom: "none"
    },
    borderRadius: 4,
    background: theme.palette.background.paper
  }
}));
