import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import axios from 'axios'

import { setMessage } from './messages'
import { RootState } from '.'
import {
  UserProps, UserJson, User, LoginFormValues, SessionAuthState,
} from '../types/user'

const API_URL = `${process.env.API_URL}`

export const fetchUser = createAsyncThunk<UserProps, void, { state: RootState }>(
  'user/fetch',
  async (
    values: null,
    { dispatch, getState },
  ): Promise<UserProps | undefined> => {
    const { data } = await axios.get<UserJson>(
      `${API_URL}/current_user/`,
    )
    return User.fromJson(data).props
  },
)

export const login = createAsyncThunk(
  'user/login',
  async (values: LoginFormValues | null, thunkAPI: any): Promise<UserProps | undefined> => {
    try {
      const { data } = await axios.post<UserJson>(
        `${API_URL}/login/`,
        values,
      )
      return User.fromJson(data).props
    } catch (error) {
      const message = (error.response
          && error.response.data)
        || error.message
        || error.toString()
      thunkAPI.dispatch(setMessage(message))
      return thunkAPI.rejectWithValue()
    }
  },
)

const sessionAuthSlice = createSlice({
  name: 'sessionAuth',
  initialState: {
    isLoggedIn: false, isFetching: false, userIsAnonymous: false, userFetched: false,
  } as SessionAuthState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchUser.fulfilled, (state, action) => {
        if (!action.payload) return
        if (action.payload.id) {
          state.user = action.payload
          state.isLoggedIn = true
          state.isFetching = false
          state.userFetched = true
        } else {
          state.user = null
          state.isLoggedIn = false
          state.isFetching = false
          state.userFetched = true
        }
      })
      .addCase(fetchUser.pending, (state, action) => {
        state.isFetching = true
      })
      .addCase(fetchUser.rejected, (state, action) => {
        if (!action.payload) return
        state.user = null
        state.isLoggedIn = false
        state.isFetching = false
      })
      .addCase(login.fulfilled, (state, action) => {
        if (!action.payload) return
        state.user = action.payload
        state.isLoggedIn = true
        state.isFetching = false
        state.userFetched = true
      })
      .addCase(login.pending, (state, action) => {
        state.isFetching = true
      })
      .addCase(login.rejected, (state, action) => {
        if (!action.payload) return
        state.user = null
        state.isLoggedIn = false
        state.isFetching = false
      })
  },
})

export const {} = sessionAuthSlice.actions
export default sessionAuthSlice.reducer
