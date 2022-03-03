import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Organization} from "./models"

export const setFetchOrganizationsSuccess: ReduxActionCreator<Organization[]> = organizations => ({
  type: ActionType.FETCH_ORGANIZATIONS_SUCCESS,
  payload: organizations
})

export const setFetchOrganizationsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_ORGANIZATIONS_ERROR,
  payload: Error(errorMessage),
  error: true
})
