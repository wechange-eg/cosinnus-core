import {Action, ActionCreator} from "redux"

import { ActionType } from "../../constants/actions"
import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ChatTemplate} from "./effects"

export const setFetchingUserChatTemplates: ActionCreator<Action> = () => ({
  type: ActionType.FETCH_USER_CHAT_TEMPLATES
})

export const setFetchUserChatTemplatesError: ReduxErrorActionCreator<string> = errorMessage => ({
  type: ActionType.FETCH_USER_CHAT_TEMPLATES_ERROR,
  payload: Error(errorMessage),
  error: true
})

export const setFetchUserChatTemplatesSuccess: ReduxActionCreator<ChatTemplate[]> = templates => ({
  type: ActionType.FETCH_USER_CHAT_TEMPLATES_SUCCESS,
  payload: templates
})

export const setFetchingChatTeamTemplates: ActionCreator<Action> = () => ({
  type: ActionType.FETCH_TEAM_CHAT_TEMPLATES
})

export const setFetchTeamChatTemplatesError: ReduxErrorActionCreator<string> = errorMessage => ({
  type: ActionType.FETCH_TEAM_CHAT_TEMPLATES_ERROR,
  payload: Error(errorMessage),
  error: true
})

export const setFetchTeamChatTemplatesSuccess: ReduxActionCreator<ChatTemplate[]> = templates => ({
  type: ActionType.FETCH_TEAM_CHAT_TEMPLATES_SUCCESS,
  payload: templates
})

