import React from "react"
import {useHistory} from "react-router-dom"
import {connect} from "react-redux"
import {
  ErrorMessage,
  Formik,
  FormikBag,
  FormikValues,
  FormikProps,
  Field
} from "formik"
import {FormattedMessage, useIntl} from "react-intl";
import {
  CircularProgress,
  Grid,
  StyledComponentProps,
  Theme,
  withStyles
} from "@material-ui/core"
import {ThemedComponentProps} from "@material-ui/core/styles/withTheme"
import MuiAlert from "@material-ui/lab/Alert"

import { LoginButton, LoginForm, LoginGrid, LoginImg, LoginOverlay, LoginProgressTypography, LoginTextField, useInputPropsStyles } from "./style"
import {setAuthError} from "../../../stores/auth/actions"
import {RootState} from "../../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../../utils/types"
import {fetchAuthToken} from "../../../stores/auth/effects"
import {Settings} from "../../../stores/settings/models";

interface LoginProps {
  authError: string | null
  setAuthError: typeof setAuthError
  settings: Settings
  fetchAuthToken: DispatchedReduxThunkActionCreator<Promise<void>>
}

const mapStateToProps = (state: RootState) => ({
  authError: state.auth.error,
  settings: state.settings
})

const mapDispatchToProps = {
  setAuthError: setAuthError,
  fetchAuthToken
}

interface CustomThemedComponentProps extends ThemedComponentProps {
  theme: Theme & { logo: string }
}

export function LoginConnector (props: LoginProps & StyledComponentProps & CustomThemedComponentProps) {
  const { authError } = props;
  const { setAuthError, fetchAuthToken } = props;
  const { settings } = props;

  const history = useHistory();
  const intl = useIntl();
  const inputPropStyles = useInputPropsStyles()

  let errorPrompt: React.ReactElement | null = null

  if (authError != null) {
    errorPrompt = (
        <MuiAlert severity="error" variant="outlined">
          <FormattedMessage id={authError}/>
        </MuiAlert>
    )
  }

  const onSubmit = (
      values: FormikValues,
      formikBag: FormikBag<FormikProps<FormikValues>, FormikValues>
  ) => {
    setAuthError(null)
    fetchAuthToken(
        values.email,
        values.password,
        formikBag.setSubmitting,
        () => {
          history.push("/")
        }
    )
  }

  const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => {
    return (
        <LoginForm>
          <Grid item>
            <Grid item>
              <LoginImg src={settings && settings.getLogoUrl()}/>
            </Grid>
            <Grid item>{errorPrompt}</Grid>
            <Grid item>
              <ErrorMessage name="email" component="div" />
            </Grid>
            <Grid item>
              <Field
                  type="email"
                  name="email"
                  label={intl.formatMessage({ id: 'E-mail address' })}
                  component={LoginTextField}
                  variant="filled"
                  InputProps={{classes: inputPropStyles}}
                  fullWidth
              />
            </Grid>
            <Grid item>
              <Field
                  type="password"
                  name="password"
                  label={intl.formatMessage({ id: 'Password' })}
                  component={LoginTextField}
                  variant="filled"
                  InputProps={{classes: inputPropStyles}}
                  fullWidth
              />
            </Grid>
            <Grid item>
              <LoginButton
                  type="submit"
                  variant="contained"
                  color="primary"
                  disabled={isSubmitting}
                  fullWidth
              >
                <FormattedMessage id="Login"/>
              </LoginButton>
            </Grid>
            <Grid item>
              <LoginButton
                  disabled={isSubmitting}
                  fullWidth
                  href="https://staging.wechange.de/password_reset/"
              >
                <FormattedMessage id="Forgot your password?" />
              </LoginButton>
            </Grid>
            {isSubmitting &&
            <LoginOverlay>
              <CircularProgress color="primary" style={{color: props.theme.palette.text.primary}}/>
              <LoginProgressTypography>
                <FormattedMessage id="Logging in..." />
              </LoginProgressTypography>
            </LoginOverlay>
            }
          </Grid>
        </LoginForm>
    )
  }

  return (
      <LoginGrid container direction="row" justify="center" alignItems="center">
        <Formik
            initialValues={{
              email: `${process.env.USER_EMAIL || ""}`,
              password: `${process.env.USER_PASSWORD || ""}`
            }}
            onSubmit={onSubmit}
        >
          {getForm}
        </Formik>
      </LoginGrid>
  )
}

const LoginConnectorWithStyles = withStyles(_ => {
}, {withTheme: true})(
    LoginConnector
)

export const Login = connect(mapStateToProps, mapDispatchToProps)(LoginConnectorWithStyles)
