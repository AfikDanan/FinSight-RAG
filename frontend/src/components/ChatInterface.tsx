import React, { useState } from 'react'
import {
    Box,
    Paper,
    TextField,
    Button,
    Typography,
    List,
    ListItem,
    Avatar,
    Chip,
    CircularProgress
} from '@mui/material'
import {
    Send as SendIcon,
    Person as PersonIcon,
    SmartToy as BotIcon
} from '@mui/icons-material'
import { useAppStore } from '../store/useAppStore'

export const ChatInterface: React.FC = () => {
    const [inputMessage, setInputMessage] = useState('')
    const { messages, isTyping, companyContext, sendMessage } = useAppStore()

    const handleSendMessage = async () => {
        if (!inputMessage.trim() || isTyping) return

        await sendMessage(inputMessage.trim())
        setInputMessage('')
    }

    const handleKeyPress = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            handleSendMessage()
        }
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '600px' }}>
            {/* Company context header */}
            {companyContext && (
                <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Typography variant="subtitle1" fontWeight="bold">
                            {companyContext.ticker}
                        </Typography>
                        <Chip
                            label={`${companyContext.timeRangeProcessed} years of data`}
                            size="small"
                            color="primary"
                        />
                        <Chip
                            label={`${companyContext.documentsAvailable} documents`}
                            size="small"
                            variant="outlined"
                        />
                    </Box>
                </Paper>
            )}

            {/* Messages area */}
            <Paper
                variant="outlined"
                sx={{
                    flex: 1,
                    overflow: 'auto',
                    mb: 2,
                    display: 'flex',
                    flexDirection: 'column'
                }}
            >
                {messages.length === 0 ? (
                    <Box sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        flexDirection: 'column',
                        gap: 2,
                        p: 4,
                        textAlign: 'center'
                    }}>
                        <BotIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
                        <Typography variant="h6" color="text.secondary">
                            Ready to analyze {companyContext?.ticker}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Ask questions about financial performance, business metrics, or regulatory filings.
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
                            <Chip
                                label="What was the revenue last year?"
                                variant="outlined"
                                size="small"
                                onClick={() => setInputMessage("What was the revenue last year?")}
                                clickable
                            />
                            <Chip
                                label="Show me the key risks"
                                variant="outlined"
                                size="small"
                                onClick={() => setInputMessage("Show me the key risks")}
                                clickable
                            />
                            <Chip
                                label="What are the main business segments?"
                                variant="outlined"
                                size="small"
                                onClick={() => setInputMessage("What are the main business segments?")}
                                clickable
                            />
                        </Box>
                    </Box>
                ) : (
                    <List sx={{ flex: 1, p: 1 }}>
                        {messages.map((message) => (
                            <ListItem
                                key={message.id}
                                sx={{
                                    display: 'flex',
                                    flexDirection: message.type === 'user' ? 'row-reverse' : 'row',
                                    alignItems: 'flex-start',
                                    gap: 1,
                                    mb: 2
                                }}
                            >
                                <Avatar
                                    sx={{
                                        bgcolor: message.type === 'user' ? 'primary.main' : 'secondary.main',
                                        width: 32,
                                        height: 32
                                    }}
                                >
                                    {message.type === 'user' ? (
                                        <PersonIcon sx={{ fontSize: 18 }} />
                                    ) : (
                                        <BotIcon sx={{ fontSize: 18 }} />
                                    )}
                                </Avatar>
                                <Paper
                                    elevation={1}
                                    sx={{
                                        p: 2,
                                        maxWidth: '70%',
                                        bgcolor: message.type === 'user' ? 'primary.light' : 'background.paper',
                                        color: message.type === 'user' ? 'primary.contrastText' : 'text.primary'
                                    }}
                                >
                                    <Typography variant="body2">
                                        {message.content}
                                    </Typography>
                                    {message.citations && message.citations.length > 0 && (
                                        <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                            {message.citations.map((citation) => (
                                                <Chip
                                                    key={citation.id}
                                                    label={citation.documentTitle}
                                                    size="small"
                                                    variant="outlined"
                                                    clickable
                                                />
                                            ))}
                                        </Box>
                                    )}
                                </Paper>
                            </ListItem>
                        ))}
                        {isTyping && (
                            <ListItem sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}>
                                    <BotIcon sx={{ fontSize: 18 }} />
                                </Avatar>
                                <Paper elevation={1} sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CircularProgress size={16} />
                                    <Typography variant="body2" color="text.secondary">
                                        Analyzing...
                                    </Typography>
                                </Paper>
                            </ListItem>
                        )}
                    </List>
                )}
            </Paper>

            {/* Input area */}
            <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                    fullWidth
                    multiline
                    maxRows={3}
                    placeholder="Ask a question about the company..."
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={isTyping}
                />
                <Button
                    variant="contained"
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim() || isTyping}
                    sx={{ minWidth: 'auto', px: 2 }}
                >
                    <SendIcon />
                </Button>
            </Box>
        </Box>
    )
}