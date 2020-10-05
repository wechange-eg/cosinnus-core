import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {RootState} from "../rootReducer"
import {
  setFetchingUserChatTemplates,
  setFetchTeamChatTemplatesSuccess,
  setFetchUserChatTemplatesError,
  setFetchUserChatTemplatesSuccess
} from "./actions"

export interface ChatTemplate {
  id: number
  message: string
  team?: string
}

/**
 * Fetch user chat templates
 *
 * @returns {(dispatch: Dispatch, getState: () => RootState) => void} - return function
 */
export const fetchUserChatTemplates: ReduxThunkActionCreator<[], void> = () => (
  dispatch: Dispatch,
  getState: () => RootState
) => {
  const headers = new Headers()
  const {authToken} = getState()
  headers.append("Authorization", "JWT " + authToken)
  dispatch(setFetchingUserChatTemplates())
  fetch(`${process.env.BASE_URL}/api/user_chat_message_templates/`, {
    method: "GET",
    headers
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: ChatTemplate[]) => {
        dispatch(setFetchUserChatTemplatesSuccess(data))
      })
    } else {
      dispatch(setFetchUserChatTemplatesError(response.statusText))
    }
  })
}

/**
 * Create user chat template
 *
 * @param message - template message
 * @returns {(dispatch: any, getState: () => RootState) => Promise<void>} - return function
 */
export const createUserChatTemplate: ReduxThunkActionCreator<[string],
  Promise<void>> = message => (dispatch: any, getState: () => RootState) => {
  const headers = new Headers()
  const {authToken} = getState()
  const formData = new FormData()
  formData.append("message", message)

  headers.append("Authorization", "JWT " + authToken)
  return fetch(`${process.env.BASE_URL}/api/user_chat_message_templates/`, {
    method: "POST",
    headers: headers,
    body: formData
  }).then(response => {
    if (response.status === 201) {
      response.json().then((_data: ChatTemplate[]) => {
        dispatch(fetchUserChatTemplates())
      })
    }
  })
}

/**
 * Fetch team chat templates
 *
 * @returns {(dispatch: Dispatch, getState: () => RootState) => void} - return function
 */
export const fetchTeamChatTemplates: ReduxThunkActionCreator<[], void> = () => (
  dispatch: Dispatch,
  getState: () => RootState
) => {
  const headers = new Headers()
  const {authToken} = getState()
  headers.append("Authorization", "JWT " + authToken)
  dispatch(setFetchingUserChatTemplates())
  fetch(`${process.env.BASE_URL}/api/team_chat_message_templates/`, {
    method: "GET",
    headers
  }).then(response => {
    if (response.status === 200) {
      response.json().then((templates: ChatTemplate[]) => {
        dispatch(setFetchTeamChatTemplatesSuccess(templates))
      })
    } else {
      dispatch(setFetchUserChatTemplatesError(response.statusText))
    }
  })
}

/**
 * Delete user chat template
 *
 * @param templateId - template identifier
 * @returns {(dispatch: any, getState: () => RootState) => void} - return function
 */
export const deleteUserChatTemplate: ReduxThunkActionCreator<[number],
  void> = templateId => (dispatch: any, getState: () => RootState) => {
  const headers = new Headers()
  const {authToken} = getState()
  headers.append("Authorization", "JWT " + authToken)
  fetch(
    `${process.env.BASE_URL}/api/user_chat_message_templates/${templateId}/`,
    {
      method: "DELETE",
      headers
    }
  ).then(response => {
    if (response.status === 204) {
      dispatch(fetchUserChatTemplates())
    }
  })
}

/**
 * Get user and team chat templates
 *
 * @returns {(dispatch: any) => Promise<any[]>} - return function
 */
export const getTemplates: ReduxThunkActionCreator<[], void> = () => (
  dispatch: any
) =>
  Promise.all([
    dispatch(fetchUserChatTemplates()),
    dispatch(fetchTeamChatTemplates())
  ])
